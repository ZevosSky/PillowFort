# 02 — Instance, Device, and Queues

**Goal:** a `VulkanInstance` that picks a GPU and prints its name, with
validation enabled and no leaks at shutdown. Nothing calls it until Chapter
05's `main`, so this chapter's runtime checks wait until then.

**ROADMAP:** step 3, and step 2's window (section 4).

**Module:** `VulkanGraphics`, namespace `pf::vulkan_graphics`.

**Prerequisites:** Chapter 01 — the workspace, and its warning to rerun
`GenerateProjects.bat` after adding files. This chapter adds six.

---

## The shape of this chapter

Five objects, created in this order and destroyed in exactly the reverse:

```text
VkInstance                 which API version, which layers, which instance extensions
  VkDebugUtilsMessengerEXT where validation messages go
  VkSurfaceKHR             the GLFW window, wrapped, so we can ask about presentation
  VkPhysicalDevice         chosen, never created
  VkDevice                 + VkQueue handles
```

Each one needs the one above it to exist first, which is why the order is
forced rather than stylistic: the messenger is created *from* the instance, the
surface wraps a window *for* an instance, "can this queue present to this
surface" is a question you cannot ask before the surface exists, and the device
is created from the physical device you picked using that answer.

### What you are actually writing

`VulkanInstance` owns all five handles. One public entry point, five private
steps, in this order — and the section that covers each:

```cpp
class VulkanInstance
{
public:
    // The window comes from the Window module. We borrow it; we do not own it.
    // preferredGpu is part of a device name ("RTX", "Radeon"), from the command
    // line in Chapter 05; empty means choose automatically. Section 5.
    InitializationResult Initialize(GLFWwindow* window, bool enableValidation,
                                    std::string_view preferredGpu);

    // Safe after a failed or partial Initialize: every handle is checked.
    void Shutdown();

    // What Chapters 03-08 borrow. Valid only after Initialize succeeds.
    VkInstance       Instance() const       { return m_instance; }
    VkPhysicalDevice PhysicalDevice() const { return m_physicalDevice; }
    VkDevice         Device() const         { return m_device; }
    VkSurfaceKHR     Surface() const        { return m_surface; }
    VkQueue          GraphicsQueue() const  { return m_graphicsQueue; }
    uint32_t         GraphicsFamily() const { return m_graphicsFamily; }

private:
    InitializationResult CreateInstance(bool enableValidation);  // sections 1-2
    InitializationResult CreateMessenger();                      // section 3
    InitializationResult CreateSurface(GLFWwindow* window);      // section 4
    InitializationResult SelectPhysicalDevice(std::string_view preferredGpu);   // section 5
    InitializationResult CreateDevice();                         // section 6

    VkInstance               m_instance       = VK_NULL_HANDLE;
    VkDebugUtilsMessengerEXT m_messenger      = VK_NULL_HANDLE;
    VkSurfaceKHR             m_surface        = VK_NULL_HANDLE;
    VkPhysicalDevice         m_physicalDevice = VK_NULL_HANDLE;   // not destroyed
    VkDevice                 m_device         = VK_NULL_HANDLE;
    VkQueue                  m_graphicsQueue  = VK_NULL_HANDLE;   // not destroyed
    uint32_t                 m_graphicsFamily = VK_QUEUE_FAMILY_IGNORED;

    // What we actually got, which is not always what was asked for: a Debug
    // build on a machine without the SDK asks for validation and gets none.
    bool                     m_validationEnabled = false;
};
```

That declaration is `VulkanInstance.h`, inside `namespace pf::vulkan_graphics`.
The header needs only `InitializationResult.h`, `<vulkan/vulkan.h>`,
`<string_view>`, and a forward declaration — `struct GLFWwindow;` — so that nothing including it drags
in GLFW. The `.cpp` includes the real `<GLFW/glfw3.h>`.

`Initialize` is then just the order, made literal — each step bailing out with
a message rather than continuing into a cascade of failures:

```cpp
InitializationResult VulkanInstance::Initialize(GLFWwindow* window, bool enableValidation,
                                                std::string_view preferredGpu)
{
    if (auto result = CreateInstance(enableValidation); !result) { return result; }
    if (m_validationEnabled)
    {
        if (auto result = CreateMessenger(); !result) { return result; }
    }
    if (auto result = CreateSurface(window);  !result) { return result; }
    if (auto result = SelectPhysicalDevice(preferredGpu); !result) { return result; }
    if (auto result = CreateDevice();         !result) { return result; }

    return InitializationResult::success();
}
```

**Read that as the table of contents for the rest of the chapter.** Every code
block below drops into one of those five functions, and each section says which.

If `Initialize` fails, the caller still calls `Shutdown` — whatever was created
before the failing step needs destroying, and section 8's `Shutdown` checks each
handle for exactly that reason.

### Where everything lands in the .cpp

Not all of it is a member. Seven helpers are plain file-scope functions above the
namespace block — Vulkan calls `debugCallback` through a raw function pointer so
it cannot be a member, and the others need no access to the class. The whole
file, in order:

```text
VulkanInstance.cpp
  includes                                            section 1
  static debugCallback(...)                           section 3
  static makeMessengerInfo()                          section 3
  static isLayerAvailable(name)                       section 1
  static hasDeviceExtension(device, name)             section 5
  static hasRequiredFeatures(device)                  section 5
  struct QueueFamilySelection                         section 5
  static selectQueueFamilies(device, surface)         section 5
  static rejectionReason(device, surface)             section 5
  namespace pf::vulkan_graphics {
      VulkanInstance::Initialize(window, validation, gpu)  above
      VulkanInstance::CreateInstance(validation)      sections 1-2
      VulkanInstance::CreateMessenger()               section 3
      VulkanInstance::CreateSurface(window)           section 4
      VulkanInstance::SelectPhysicalDevice(gpu)       section 5
      VulkanInstance::CreateDevice()                  section 6
      VulkanInstance::Shutdown()                      section 8
  }
```

Order matters only in that each `static` must appear before its first use, which
the layout above already satisfies. If you would rather forward-declare them at
the top and define them at the bottom, nothing here breaks.

Two things that are *not* in this chapter, so you are not waiting for them:
the swapchain (Chapter 03, and it needs the surface and device from here), and
anything that draws (Chapter 05). Nothing here puts a pixel on screen. The
payoff is that from here on, mistakes get *reported* instead of silently
producing a black window.

---

## 0. The result type every step returns

The roadmap's convention is that constructors do not perform fallible GPU
initialization — a separate `Initialize()` returns a descriptive result, and
unsupported hardware is *reported*, not asserted and not thrown. Every one of
the five steps above returns this, and so does every `Initialize` from here to
Chapter 07, so it is worth writing before the first one needs it:

```cpp
///========================================================
/// @author Gary Yang
/// @brief  Result of a fallible initialize()
/// @copyright (C) Gary 2026
///========================================================

#pragma once

#include <string>
#include <utility>

class InitializationResult {
public:
    static InitializationResult success() { return { true, {} }; }
    static InitializationResult failure(std::string message) {
        return { false, std::move(message) };
    }

    // explicit: `if (result)` works, `bool ok = result` does not compile.
    explicit operator bool() const { return m_succeeded; }
    const char* message() const { return m_message.c_str(); }

private:
    InitializationResult(bool succeeded, std::string message)
        : m_succeeded(succeeded), m_message(std::move(message)) {}

    bool        m_succeeded = false;
    std::string m_message;
};
```

`failure` takes a `std::string` rather than a `const char*` so the message can
carry the values that make it useful — which layer was missing, which device was
rejected and why. A failure message that does not name the thing that failed
costs you the debugging session it was supposed to save.

---

## 1. The instance

**This is `CreateInstance`, first half.** It gathers the three things
`vkCreateInstance` needs — the API version you are coding against, the layers
you want, and the instance-level extensions you need. Section 2 assembles them
and makes the call; the function is not finished until you have read both.

Two terms first. A **layer** is a library the loader inserts between your
calls and the driver; the validation layer checks every call against the
specification and reports what it finds through the messenger in section 3. An
**extension** adds functions and types the core API does not have. Instance
extensions are the ones that exist before any GPU is chosen: here, the ones
that let Vulkan draw into a window, and the messenger itself.

```cpp
// Source/PillowFort/VulkanGraphics/VulkanInstance.cpp
#include "PillowFort/VulkanGraphics/VulkanInstance.h"

#include "PillowFort/ErrorReporting/DebugBreak.h"
#include "PillowFort/ErrorReporting/InitializationResult.h"
#include "PillowFort/ErrorReporting/Log.h"

#include <vulkan/vulkan.h>
#include <GLFW/glfw3.h>   // after vulkan.h: glfwCreateWindowSurface is only declared
                          // when GLFW sees the Vulkan headers already included

#include <vulkan/vk_enum_string_helper.h>   // string_VkResult, for error messages

#include <cstring>   // std::strcmp, for the layer and extension checks
#include <format>    // std::format, for error messages
#include <string>    // the device-rejection list in section 5
#include <string_view>
#include <vector>

// The static helpers go here, above the namespace: debugCallback and
// makeMessengerInfo from section 3, isLayerAvailable from section 1, and the
// device-selection helpers from section 5. See "Where everything lands" above.

namespace pf::vulkan_graphics {

InitializationResult VulkanInstance::CreateInstance(bool enableValidation)
{
    const VkApplicationInfo applicationInfo{
        .sType              = VK_STRUCTURE_TYPE_APPLICATION_INFO,
        .pApplicationName   = "SandboxGame",
        .applicationVersion = VK_MAKE_VERSION(0, 1, 0),
        .pEngineName        = "PillowFort",
        .engineVersion      = VK_MAKE_VERSION(0, 1, 0),
        .apiVersion         = VK_API_VERSION_1_3,
    };

    // GLFW knows which surface extensions this platform needs.
    // On Windows this is VK_KHR_surface + VK_KHR_win32_surface.
    uint32_t glfwExtensionCount = 0;
    const char** glfwExtensions = glfwGetRequiredInstanceExtensions(&glfwExtensionCount);
    if (glfwExtensions == nullptr)
    {
        return InitializationResult::failure(
            "GLFW reports no Vulkan surface extensions. No installed driver supports presentation.");
    }

    std::vector<const char*> instanceExtensions(glfwExtensions,
                                                glfwExtensions + glfwExtensionCount);
    std::vector<const char*> layers;

    // Ask for validation only if it is actually installed. isLayerAvailable is
    // below; on a machine without the SDK this branch simply does not fire and
    // you get a working Debug build instead of VK_ERROR_LAYER_NOT_PRESENT.
    // Everything downstream - the pNext chain in section 2, the messenger in
    // section 3 - keys off this member, not off what was requested.
    m_validationEnabled = enableValidation && isLayerAvailable("VK_LAYER_KHRONOS_validation");

    if (m_validationEnabled)
    {
        instanceExtensions.push_back(VK_EXT_DEBUG_UTILS_EXTENSION_NAME);
        // Provided by the validation layer itself; required before section 2
        // may chain VkLayerSettingsCreateInfoEXT.
        instanceExtensions.push_back(VK_EXT_LAYER_SETTINGS_EXTENSION_NAME);
        layers.push_back("VK_LAYER_KHRONOS_validation");
    }
    else if (enableValidation)
    {
        Log::warning("VK_LAYER_KHRONOS_validation not installed. Continuing without validation.");
    }

    // >>> Section 2 continues this function here: build the pNext chain,
    //     call vkCreateInstance, and check its VkResult. <<<
}

} // namespace pf::vulkan_graphics
```

`m_instance` is a member, so nothing is returned — the next section fills it in
and this function ends by reporting success or the specific `VkResult` that
failed.

Two things worth pausing on.

**`apiVersion` is a promise, not a request.** It tells the loader and the
validation layer which version's rules to hold you to. Requesting 1.3 on a
driver that only exposes 1.2 makes `vkCreateInstance` fail with
`VK_ERROR_INCOMPATIBLE_DRIVER`, which is exactly what you want — a clear error
instead of undefined behavior at the first `vkCmdBeginRendering`.

Your SDK headers are 1.4, so `VK_API_VERSION_1_4` is available. **Stay on 1.3.**
Everything the roadmap needs is 1.3 core, 1.4 drivers are less universally
deployed, and 1.4's headline features (`maintenance5`/`6`, `pushDescriptor` in
core, `hostImageCopy`) are conveniences you will not miss. Bumping later is a
one-line change.

**Always enumerate before you request.** Asking for a layer that is not
installed fails instance creation with `VK_ERROR_LAYER_NOT_PRESENT`, and the
message does not tell you which layer. On a machine without the SDK — which is
every machine that is not yours — this turns your Debug build into an
immediate crash. Check first and degrade gracefully:

```cpp
// File scope, above the namespace block. Needs nothing from the class.
static bool isLayerAvailable(const char* name)
{
    uint32_t count = 0;
    vkEnumerateInstanceLayerProperties(&count, nullptr);
    std::vector<VkLayerProperties> available(count);
    vkEnumerateInstanceLayerProperties(&count, available.data());

    for (const VkLayerProperties& layer : available)
    {
        if (std::strcmp(layer.layerName, name) == 0) { return true; }
    }
    return false;
}
```

This **enumerate-count-then-enumerate-again** pattern is everywhere in Vulkan.
Call with `pProperties == nullptr` to get the count, size a vector, call again
to fill it. You will write it a dozen times; wrap it once.

---

## 2. Catching errors during instance creation

**This is `CreateInstance`, second half** — it picks up exactly where the
section 1 listing stopped, with `instanceExtensions` and `layers` already
populated.

There is a bootstrapping problem: the debug messenger is created *from* an
instance, so it cannot report errors in creating that instance. The fix is that
`VkDebugUtilsMessengerCreateInfoEXT` may be chained into
`VkInstanceCreateInfo::pNext`, where the layer picks it up and uses it for the
duration of `vkCreateInstance` and `vkDestroyInstance`.

This is your first real `pNext` chain, and the pattern is worth internalizing
now because device creation uses a longer one:

```cpp
// makeMessengerInfo and debugCallback are both defined in section 3. They are
// file-scope, above the namespace block, so they are already in scope here.
// Section 3 uses the same helper, which is why it is a helper and not a
// struct literal typed out twice.
VkDebugUtilsMessengerCreateInfoEXT messengerInfo = makeMessengerInfo();

// Opt in to the check that is off by default: synchronization validation.
// VK_EXT_layer_settings is the current way to configure the layer from code.
// "enables" is the older setting name - see the note after this block.
const char* const enables[] = { "VK_VALIDATION_FEATURE_ENABLE_SYNCHRONIZATION_VALIDATION_EXT" };
// And make it follow what shaders read and write through descriptors, which
// it ignores by default - see "One blind spot" after this block.
const VkBool32 trackShaderAccesses = VK_TRUE;
const VkLayerSettingEXT validationSettings[] = {
    { .pLayerName   = "VK_LAYER_KHRONOS_validation",
      .pSettingName = "enables",
      .type         = VK_LAYER_SETTING_TYPE_STRING_EXT,
      .valueCount   = 1,
      .pValues      = enables },
    { .pLayerName   = "VK_LAYER_KHRONOS_validation",
      .pSettingName = "syncval_shader_accesses_heuristic",
      .type         = VK_LAYER_SETTING_TYPE_BOOL32_EXT,
      .valueCount   = 1,
      .pValues      = &trackShaderAccesses },
};

VkLayerSettingsCreateInfoEXT layerSettings{
    .sType        = VK_STRUCTURE_TYPE_LAYER_SETTINGS_CREATE_INFO_EXT,
    .pNext        = &messengerInfo,
    .settingCount = 2,
    .pSettings    = validationSettings,
};

// m_validationEnabled, not enableValidation: without the layer, neither
// extension above was enabled, and chaining their structs is invalid.
const VkInstanceCreateInfo instanceInfo{
    .sType                   = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO,
    .pNext                   = m_validationEnabled ? &layerSettings : nullptr,
    .pApplicationInfo        = &applicationInfo,
    .enabledLayerCount       = static_cast<uint32_t>(layers.size()),
    .ppEnabledLayerNames     = layers.data(),
    .enabledExtensionCount   = static_cast<uint32_t>(instanceExtensions.size()),
    .ppEnabledExtensionNames = instanceExtensions.data(),
};

const VkResult result = vkCreateInstance(&instanceInfo, nullptr, &m_instance);
if (result != VK_SUCCESS)
{
    return InitializationResult::failure(
        std::format("vkCreateInstance failed: {}", string_VkResult(result)));
}

return InitializationResult::success();
```

That is `CreateInstance` complete. `string_VkResult` comes from
`<vulkan/vk_enum_string_helper.h>` in the SDK, and it is worth the include the
first time you read `VK_ERROR_INCOMPATIBLE_DRIVER` instead of `-9`.

**What the two settings do.** The first turns on *synchronization
validation*, which watches the order in which commands read and write memory
and reports a missing barrier — Chapter 04's subject — even when the mistake
happens to work on your GPU. It costs a little speed and catches exactly the
bugs that corrupt on someone else's machine, so it is on from the start.

**The second setting**, `syncval_shader_accesses_heuristic`, makes it also
follow what shaders read and write through descriptors (Chapter 08), which by
default it does not; it is called a heuristic because it can, rarely, report a
hazard that is not one, and Chapter 20 section 5 shows what it still cannot see.

**Expect one warning on every Debug start**, saying that `"enables"` is
deprecated. It is deliberate: a `vkconfig` override (Chapter 01 section 5) can
switch off `"validate_sync"` but leaves `"enables"` alone.

**Do not trust that it is on until you have seen it fire.** An override, or a
`VK_LAYER_*` environment variable, can switch it off with no message, so a
clean run looks exactly like a correct one. Chapter 05's exit check has the
positive control: one deliberately wrong barrier that must produce a
`SYNC-HAZARD` error. If it stays silent, setting `VK_LAYER_VALIDATE_SYNC=1` for
your own process forces it on while you find out why.

The `pNext` rules, since they are easy to get subtly wrong:

- Each struct in the chain sets its own `sType`. The loader walks the chain by
  reading `sType` from each node.
- Order does not matter.
- The chain must outlive the create call. Every struct above is a stack local
  in the same scope as `vkCreateInstance` — that is deliberate. A `pNext`
  pointing at a destroyed temporary is a classic and very confusing crash.
- Chaining a struct whose extension you did not enable is ignored at best and a
  validation error at worst.

---

## 3. The debug callback

Two pieces here, and they live in different places. The callback itself is a
free function at file scope — it is not a member, because Vulkan calls it
through a plain function pointer. Creating the messenger is `CreateMessenger`,
which runs after `CreateInstance` succeeds.

`PF_DEBUG_BREAK` does not exist yet — write it first. One macro, and it is the
reason the next block is worth anything:

```cpp
// Source/PillowFort/ErrorReporting/DebugBreak.h
#pragma once

#ifdef PF_DEBUG
    #include <windows.h>   // IsDebuggerPresent; premake defines WIN32_LEAN_AND_MEAN and NOMINMAX
    // Break only when a debugger is there to catch it. Without one, __debugbreak
    // ends the process on the spot (exit code 0x80000003) - which turns a logged
    // validation error in a command-line run into what looks like a crash.
    #define PF_DEBUG_BREAK() do { if (IsDebuggerPresent()) { __debugbreak(); } } while (0)
#else
    #define PF_DEBUG_BREAK() ((void)0)
#endif
```

```cpp
// File scope, above the namespace block.
static VKAPI_ATTR VkBool32 VKAPI_CALL debugCallback(
    VkDebugUtilsMessageSeverityFlagBitsEXT severity,
    VkDebugUtilsMessageTypeFlagsEXT types,
    const VkDebugUtilsMessengerCallbackDataEXT* callbackData,
    void* /*userData*/)
{
    // The message ID (a VUID, or a name like SYNC-HAZARD-WRITE-AFTER-WRITE) is what
    // you search for, and recent layers no longer repeat it inside pMessage. The
    // spec allows it to be null.
    const char* const messageId =
        callbackData->pMessageIdName != nullptr ? callbackData->pMessageIdName : "no ID";
    const std::string text = std::format("Vulkan [{}]: {}", messageId, callbackData->pMessage);

    const bool isError = (severity & VK_DEBUG_UTILS_MESSAGE_SEVERITY_ERROR_BIT_EXT) != 0;
    if (isError)
    {
        Log::error(text.c_str());
    }
    else
    {
        Log::warning(text.c_str());
    }

    // Break on errors the validation layer found in *our* calls. The loader and
    // other installed layers (overlays, capture tools) report through this same
    // callback as GENERAL messages; their complaints are not bugs in this code.
    if (isError && (types & VK_DEBUG_UTILS_MESSAGE_TYPE_VALIDATION_BIT_EXT) != 0)
    {
        // Break here so the debugger stops on the offending call, not several
        // frames later.
        PF_DEBUG_BREAK();
    }

    // VK_FALSE means "do not abort the call that triggered this".
    // VK_TRUE is reserved for layer development and will break your app.
    return VK_FALSE;
}
```

Print the ID, not just the text. `pMessage` is written for people and its
format changes between layer releases — from 1.4.363 on, the ID such as
`SYNC-HAZARD-WRITE-AFTER-WRITE` is no longer repeated inside it — while
`pMessageIdName` is the stable name every exit check in this tutorial tells you
to look for, and the one to paste into a search.

Expect some messages that are not about your code at all. The loader reports
through this callback too, and so does every implicit layer installed on the
machine — an overlay from a game launcher warning that it found itself twice
is typical, and harmless. That is why the break checks the message type.

**Break on validation errors in Debug.** This is the single highest-value habit
in this whole tutorial. The stack at the break points directly at the offending
`vkCmd*` call. Without it you get a message with no context and have to bisect.

Both section 2 and `CreateMessenger` need the same create-info, so it is a
helper rather than a struct literal written out twice. Section 2's `pNext`
chain covers instance creation and teardown; the messenger covers everything
in between.

```cpp
// File scope, above the namespace block. Section 2 calls this too.
static VkDebugUtilsMessengerCreateInfoEXT makeMessengerInfo()
{
    return {
        .sType           = VK_STRUCTURE_TYPE_DEBUG_UTILS_MESSENGER_CREATE_INFO_EXT,
        .messageSeverity = VK_DEBUG_UTILS_MESSAGE_SEVERITY_WARNING_BIT_EXT
                         | VK_DEBUG_UTILS_MESSAGE_SEVERITY_ERROR_BIT_EXT,
        .messageType     = VK_DEBUG_UTILS_MESSAGE_TYPE_GENERAL_BIT_EXT
                         | VK_DEBUG_UTILS_MESSAGE_TYPE_VALIDATION_BIT_EXT
                         | VK_DEBUG_UTILS_MESSAGE_TYPE_PERFORMANCE_BIT_EXT,
        .pfnUserCallback = &debugCallback,
        .pUserData       = nullptr,
    };
}
```

**This is `CreateMessenger`.** Because `VK_EXT_debug_utils` is an extension,
its functions are not exported by `vulkan-1.dll`; they must be looked up with
`vkGetInstanceProcAddr`:

```cpp
InitializationResult VulkanInstance::CreateMessenger()
{
    const VkDebugUtilsMessengerCreateInfoEXT messengerInfo = makeMessengerInfo();

    auto createMessenger = reinterpret_cast<PFN_vkCreateDebugUtilsMessengerEXT>(
        vkGetInstanceProcAddr(m_instance, "vkCreateDebugUtilsMessengerEXT"));

    // Initialize only calls this when m_validationEnabled is true, which means
    // VK_EXT_debug_utils was enabled, so this should never be null. If it is,
    // losing messages is not worth refusing to start over.
    if (createMessenger == nullptr)
    {
        Log::warning("vkCreateDebugUtilsMessengerEXT not found. Continuing without a messenger.");
        return InitializationResult::success();
    }

    const VkResult result =
        createMessenger(m_instance, &messengerInfo, nullptr, &m_messenger);
    if (result != VK_SUCCESS)
    {
        return InitializationResult::failure(
            std::format("vkCreateDebugUtilsMessengerEXT failed: {}",
                        string_VkResult(result)));
    }
    return InitializationResult::success();
}
```

(Chapter 33 section 6 loads five more extension functions by name, for
acceleration structures. They belong to the device rather than the instance,
so it looks them up with `vkGetDeviceProcAddr` instead.)

---

## 4. The window, and the surface

Section 5 has to ask whether a queue can present to the window, and Vulkan
only answers that about a `VkSurfaceKHR`: the window, wrapped. So this section
writes the window first, then wraps it.

### The window module (ROADMAP step 2)

**ROADMAP step 2 — the window and frame loop — has no chapter of its own**, so
here is the `Window` module every later chapter uses. It is short, which is why
it did not get a chapter, but its shape matters: Chapter 05's frame loop, Chapter
03's resize handling, and Chapter 07's input forwarding all call into it.

```cpp
// Source/PillowFort/Window/GlfwWindow.h
#pragma once

#include "PillowFort/ErrorReporting/InitializationResult.h"

#include <GLFW/glfw3.h>   // callback typedefs; Chapter 07's InputForwarding uses them
#include <vector>

namespace pf::window {

struct WindowConfig
{
    int         width  = 1280;
    int         height = 720;
    const char* title  = "PillowFort";
};

enum class EventKind { FramebufferResized, Key, MouseButton, Scroll, CursorPosition };

// One queued event. The GLFW callbacks push these; the frame loop drains them
// once per frame (ROADMAP step 2).
struct Event
{
    EventKind kind   = EventKind::FramebufferResized;
    int       code   = 0;     // key or mouse button
    int       action = 0;     // GLFW_PRESS, GLFW_RELEASE, GLFW_REPEAT
    int       mods   = 0;
    double    x      = 0.0;   // scroll offset or cursor position
    double    y      = 0.0;

    static Event framebufferResized()                  { return { EventKind::FramebufferResized }; }
    static Event key(int keyCode, int act, int mod)    { return { EventKind::Key, keyCode, act, mod }; }
    static Event mouseButton(int button, int act, int mod) { return { EventKind::MouseButton, button, act, mod }; }
    static Event scroll(double dx, double dy)          { return { EventKind::Scroll, 0, 0, 0, dx, dy }; }
    static Event cursorPosition(double px, double py)  { return { EventKind::CursorPosition, 0, 0, 0, px, py }; }

    bool isKeyboard() const { return kind == EventKind::Key; }
    bool isMouse() const
    {
        return kind == EventKind::MouseButton || kind == EventKind::Scroll ||
               kind == EventKind::CursorPosition;
    }
};

// Chapter 07 section 4 declares InputForwarding here, above the class.

class GlfwWindow
{
public:
    InitializationResult initialize(const WindowConfig& config);
    void shutdown();

    GLFWwindow* handle() const      { return m_window; }
    bool        shouldClose() const { return glfwWindowShouldClose(m_window) == GLFW_TRUE; }
    bool        isMinimized() const;   // framebuffer size is zero
    void        pollEvents()        { glfwPollEvents(); }
    void        waitEvents()        { glfwWaitEvents(); }

    // Everything queued since the last call. Call once per frame.
    std::vector<Event> drainEvents();

    // Chapter 07 adds: void setInputForwarding(const InputForwarding& forwarding);

private:
    static GlfwWindow* self(GLFWwindow* window)
    {
        return static_cast<GlfwWindow*>(glfwGetWindowUserPointer(window));
    }
    void queueEvent(const Event& event) { m_events.push_back(event); }

    static void onFramebufferResized(GLFWwindow* window, int width, int height);
    // Chapter 07 adds onKey, onChar, onMouseButton, onScroll, onCursorPos,
    // onCursorEnter, and onWindowFocus.

    GLFWwindow*        m_window = nullptr;
    std::vector<Event> m_events;
    // Chapter 07 adds: InputForwarding m_forwarding;
};

} // namespace pf::window
```

```cpp
// Source/PillowFort/Window/GlfwWindow.cpp, inside namespace pf::window
InitializationResult GlfwWindow::initialize(const WindowConfig& config)
{
    if (glfwInit() != GLFW_TRUE)
    {
        return InitializationResult::failure("glfwInit failed. No display?");
    }

    // Without this GLFW creates an OpenGL context, which conflicts with Vulkan.
    glfwWindowHint(GLFW_CLIENT_API, GLFW_NO_API);

    m_window = glfwCreateWindow(config.width, config.height, config.title, nullptr, nullptr);
    if (m_window == nullptr)
    {
        return InitializationResult::failure("glfwCreateWindow failed.");
    }

    // The resize event Chapter 03 reacts to. GLFW hands back the void* stored here.
    glfwSetWindowUserPointer(m_window, this);
    glfwSetFramebufferSizeCallback(m_window, &GlfwWindow::onFramebufferResized);
    // Chapter 07 registers its input callbacks here the same way.
    return InitializationResult::success();
}

void GlfwWindow::shutdown()
{
    // After VulkanRenderer::shutdown: the surface must already be gone.
    if (m_window != nullptr)
    {
        glfwDestroyWindow(m_window);
        m_window = nullptr;
    }
    glfwTerminate();
}

bool GlfwWindow::isMinimized() const
{
    int width = 0;
    int height = 0;
    glfwGetFramebufferSize(m_window, &width, &height);
    return width == 0 || height == 0;
}

std::vector<Event> GlfwWindow::drainEvents()
{
    std::vector<Event> events;
    events.swap(m_events);   // hands back everything queued and leaves the queue empty
    return events;
}

void GlfwWindow::onFramebufferResized(GLFWwindow* window, int /*width*/, int /*height*/)
{
    self(window)->queueEvent(Event::framebufferResized());
}
```

One ordering rule is easy to get wrong, and its failure is confusing:
`glfwInit()` must run before `vkCreateInstance`, because
`glfwGetRequiredInstanceExtensions` returns `nullptr` until it has.

One Windows behavior worth deciding about while you write step 2, because it
changes what Chapter 05's resize stress test can show you: **while the user
drags a window edge, Win32 runs its own modal message loop, and
`glfwPollEvents` does not return until they let go.** Your frame loop is frozen
for the whole drag, so the swapchain is recreated once, on release, and the
window shows stale contents meanwhile. That is acceptable, and it is what this
tutorial assumes. If you want live resizing, the standard fix is to also draw a
frame from `glfwSetWindowRefreshCallback`, which GLFW keeps calling during the
drag — at the price of rendering from inside a callback.

### The surface

**This is `CreateSurface`.** It runs third, after the instance and messenger
exist, and before device selection — because "can this queue family present to
this surface" is a question about a specific surface, and section 5 has to ask
it.

```cpp
InitializationResult VulkanInstance::CreateSurface(GLFWwindow* window)
{
    // The Window module owns the GLFWwindow*; VulkanGraphics borrows it.
    const VkResult result = glfwCreateWindowSurface(m_instance, window, nullptr, &m_surface);
    if (result != VK_SUCCESS)
    {
        return InitializationResult::failure(
            std::format("glfwCreateWindowSurface failed: {}", string_VkResult(result)));
    }
    return InitializationResult::success();
}
```

At shutdown, `vkDestroySurfaceKHR` must run **before** `glfwDestroyWindow`.
ROADMAP already calls this out; it is worth restating because the crash it
produces looks like a driver bug.

---

## 5. Choosing a physical device

**This is `SelectPhysicalDevice`.** It picks `m_physicalDevice` and records
`m_graphicsFamily`; it creates nothing, so there is nothing to destroy later.

This is where most hand-written Vulkan gets sloppy — "pick the first discrete
GPU" works on your machine and fails on a laptop with a disabled dGPU. Check
actual requirements instead, and only then express a preference.

For each `VkPhysicalDevice`, ask these questions, **in this order**:

1. Does it support Vulkan 1.3? (`VkPhysicalDeviceProperties::apiVersion`)
2. Does it support `VK_KHR_swapchain`?
3. Does it support `dynamicRendering` and `synchronization2`?
4. Does it have a queue family with graphics + compute + presentation to our
   surface?
5. Does the surface report at least one format and one present mode on it?

The order is not cosmetic. Question 3 chains `VkPhysicalDeviceVulkan13Features`
into a query, and doing that on a 1.2 device is itself invalid — so question 1
has to reject those devices first. Question 5 is the one Chapter 03 leans on:
its `chooseSurfaceFormat` falls back to `formats[0]` on the strength of it.

Questions 2 and 3 ask about two different things. An *extension*, like
`VK_KHR_swapchain`, adds functions and types. A *feature*, like
`dynamicRendering`, switches on an optional capability of something that
already exists. A device must support both, and both are then requested by
name when it is created (section 6).

Question 2 is the enumerate-twice pattern from section 1 again, over device
extensions this time:

```cpp
// File scope, above the namespace block.
static bool hasDeviceExtension(VkPhysicalDevice device, const char* name)
{
    uint32_t count = 0;
    vkEnumerateDeviceExtensionProperties(device, nullptr, &count, nullptr);
    std::vector<VkExtensionProperties> available(count);
    vkEnumerateDeviceExtensionProperties(device, nullptr, &count, available.data());

    for (const VkExtensionProperties& extension : available)
    {
        if (std::strcmp(extension.extensionName, name) == 0) { return true; }
    }
    return false;
}
```

Question 3 introduces the pattern you will use constantly:

```cpp
// File scope, above the namespace block.
static bool hasRequiredFeatures(VkPhysicalDevice device)
{
    VkPhysicalDeviceVulkan13Features features13{
        .sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_3_FEATURES,
    };
    VkPhysicalDeviceVulkan12Features features12{
        .sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_2_FEATURES,
        .pNext = &features13,
    };
    VkPhysicalDeviceFeatures2 features{
        .sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_FEATURES_2,
        .pNext = &features12,
    };

    vkGetPhysicalDeviceFeatures2(device, &features);

    return features13.dynamicRendering == VK_TRUE
        && features13.synchronization2 == VK_TRUE;
}
```

You build the chain, hand it to `vkGetPhysicalDeviceFeatures2`, and the driver
fills in every struct in it. The same chain shape, with values you *set*
instead of read, is what you pass to `vkCreateDevice`.

**Query and enable are two separate chains.** A tempting shortcut is to pass
the queried struct straight into `vkCreateDevice`, which enables every feature
the device supports. Do not. Enabling `robustBufferAccess` you never asked for
costs performance, and a feature you enabled but never verified is a portability
bug waiting to surface on different hardware. Verify what you need, then enable
exactly that.

### Queue families

A queue family is a group of identical queues with a capability mask. On
desktop GPUs you typically see:

| Family | Flags | Typical count |
| --- | --- | --- |
| 0 | graphics + compute + transfer | 1-16 |
| 1 | compute + transfer | 1-8 (async compute) |
| 2 | transfer | 1-2 (DMA engine) |

ROADMAP uses one graphics + presentation queue, which is right. Two notes
for later:

- The spec guarantees that any family with `VK_QUEUE_GRAPHICS_BIT` or
  `VK_QUEUE_COMPUTE_BIT` also supports transfer, so a single universal queue
  handles staging uploads too. `VK_QUEUE_TRANSFER_BIT` may not be listed in the
  flags even though it is supported.
- Presentation support is not a queue flag. It is a per-family, per-surface
  question: `vkGetPhysicalDeviceSurfaceSupportKHR(device, familyIndex, surface, &supported)`.

```cpp
// File scope, above the namespace block - both of these.
struct QueueFamilySelection
{
    uint32_t graphicsAndPresent = VK_QUEUE_FAMILY_IGNORED;
    bool isComplete() const { return graphicsAndPresent != VK_QUEUE_FAMILY_IGNORED; }
};

static QueueFamilySelection selectQueueFamilies(VkPhysicalDevice device, VkSurfaceKHR surface)
{
    uint32_t count = 0;
    vkGetPhysicalDeviceQueueFamilyProperties(device, &count, nullptr);
    std::vector<VkQueueFamilyProperties> families(count);
    vkGetPhysicalDeviceQueueFamilyProperties(device, &count, families.data());

    QueueFamilySelection selection;
    for (uint32_t index = 0; index < count; ++index)
    {
        const bool supportsGraphics = (families[index].queueFlags & VK_QUEUE_GRAPHICS_BIT) != 0;
        const bool supportsCompute  = (families[index].queueFlags & VK_QUEUE_COMPUTE_BIT) != 0;

        VkBool32 supportsPresent = VK_FALSE;
        vkGetPhysicalDeviceSurfaceSupportKHR(device, index, surface, &supportsPresent);

        if (supportsGraphics && supportsCompute && supportsPresent == VK_TRUE)
        {
            selection.graphicsAndPresent = index;
            break;
        }
    }
    return selection;
}
```

Requiring compute on the same family now — before you need it — means the compute
chapters (20 onward) need no device-selection changes. On every desktop GPU
family 0 satisfies all three, so this costs nothing today.

### Putting the questions together

One helper asks all five and says which one failed. Returning the reason rather
than a `bool` is what turns "no suitable GPU" into a message you can act on:

```cpp
// File scope, above the namespace block. nullptr means the device is usable.
static const char* rejectionReason(VkPhysicalDevice device, VkSurfaceKHR surface)
{
    VkPhysicalDeviceProperties properties{};
    vkGetPhysicalDeviceProperties(device, &properties);

    if (properties.apiVersion < VK_API_VERSION_1_3)                   { return "no Vulkan 1.3"; }
    if (!hasDeviceExtension(device, VK_KHR_SWAPCHAIN_EXTENSION_NAME)) { return "no VK_KHR_swapchain"; }
    if (!hasRequiredFeatures(device))                                 { return "no dynamicRendering or synchronization2"; }
    if (!selectQueueFamilies(device, surface).isComplete())           { return "no graphics + compute + present queue family"; }

    uint32_t formatCount = 0;
    vkGetPhysicalDeviceSurfaceFormatsKHR(device, surface, &formatCount, nullptr);
    uint32_t presentModeCount = 0;
    vkGetPhysicalDeviceSurfacePresentModesKHR(device, surface, &presentModeCount, nullptr);
    if (formatCount == 0 || presentModeCount == 0)                    { return "surface reports no formats or present modes"; }

    return nullptr;
}
```

`SelectPhysicalDevice` is then a loop over the devices. It skips the unusable
ones with a note of why, and **lets you choose among the rest**: a laptop with
an integrated and a discrete GPU has two good answers, and which one is better
depends on what you are testing — so the choice is a setting, not a guess
buried in code. Without a setting it prefers a discrete GPU. It logs every
usable device either way, which is what tells you what to ask for.

```cpp
InitializationResult VulkanInstance::SelectPhysicalDevice(std::string_view preferredGpu)
{
    uint32_t count = 0;
    vkEnumeratePhysicalDevices(m_instance, &count, nullptr);
    std::vector<VkPhysicalDevice> devices(count);
    vkEnumeratePhysicalDevices(m_instance, &count, devices.data());

    std::string rejected;   // every device passed over, and why
    std::string usable;     // every device that would work, for the log

    VkPhysicalDevice requested           = VK_NULL_HANDLE;   // matched preferredGpu
    VkPhysicalDevice automatic           = VK_NULL_HANDLE;   // first usable, discrete wins
    bool             automaticIsDiscrete = false;

    for (VkPhysicalDevice device : devices)
    {
        VkPhysicalDeviceProperties properties{};
        vkGetPhysicalDeviceProperties(device, &properties);
        const std::string_view name = properties.deviceName;

        if (const char* reason = rejectionReason(device, m_surface))
        {
            rejected += std::format("\n  {}: {}", name, reason);
            continue;
        }
        usable += std::format("\n  {}", name);

        // An explicit request wins: the first usable device whose name contains
        // it. Case-sensitive, so "RTX", not "rtx".
        if (!preferredGpu.empty() && requested == VK_NULL_HANDLE &&
            name.find(preferredGpu) != std::string_view::npos)
        {
            requested = device;
        }

        const bool isDiscrete = properties.deviceType == VK_PHYSICAL_DEVICE_TYPE_DISCRETE_GPU;
        if (automatic == VK_NULL_HANDLE || (isDiscrete && !automaticIsDiscrete))
        {
            automatic           = device;
            automaticIsDiscrete = isDiscrete;
        }
    }

    if (automatic == VK_NULL_HANDLE)
    {
        return InitializationResult::failure(
            std::format("No GPU meets the requirements ({} found).{}", count, rejected));
    }

    Log::info(std::format("Usable GPUs:{}", usable).c_str());
    if (!rejected.empty())
    {
        Log::info(std::format("Rejected GPUs:{}", rejected).c_str());
    }

    // A request that matches nothing is a typo or a missing driver, not a
    // reason to refuse to start. Say so, and carry on with the automatic pick.
    if (!preferredGpu.empty() && requested == VK_NULL_HANDLE)
    {
        Log::warning(std::format("No usable GPU name contains \"{}\"; choosing automatically.",
                                 preferredGpu).c_str());
    }

    m_physicalDevice = (requested != VK_NULL_HANDLE) ? requested : automatic;
    m_graphicsFamily = selectQueueFamilies(m_physicalDevice, m_surface).graphicsAndPresent;

    VkPhysicalDeviceProperties chosen{};
    vkGetPhysicalDeviceProperties(m_physicalDevice, &chosen);
    // driverVersion's encoding is vendor-specific, so print it raw rather than
    // pretend VK_API_VERSION_MAJOR applies to it.
    Log::info(std::format("GPU: {} (driver {:#x})", chosen.deviceName, chosen.driverVersion).c_str());

    return InitializationResult::success();
}
```

**A GPU you own can be missing from both lists.** `vkEnumeratePhysicalDevices`
only returns devices whose driver the Vulkan loader could load. If a GPU in the
machine appears in neither "Usable" nor "Rejected", the problem is below Vulkan:
look for it in Device Manager. A hybrid laptop's discrete GPU showing an error
state there — commonly because the laptop's power or GPU-switching mode has
turned it off — is invisible to Vulkan until that is fixed, and no code in this
chapter can see it.

---

## 6. Creating the logical device

**This is `CreateDevice`, the last step.** It uses the `m_physicalDevice` and
`m_graphicsFamily` that section 5 chose, and fills in `m_device` and
`m_graphicsQueue`.

```cpp
InitializationResult VulkanInstance::CreateDevice()
{
    const float queuePriority = 1.0f;

    const VkDeviceQueueCreateInfo queueInfo{
        .sType            = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO,
        .queueFamilyIndex = m_graphicsFamily,
        .queueCount       = 1,
        .pQueuePriorities = &queuePriority,
    };

    const char* deviceExtensions[] = { VK_KHR_SWAPCHAIN_EXTENSION_NAME };

    VkPhysicalDeviceVulkan13Features enable13{
        .sType            = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_3_FEATURES,
        .synchronization2 = VK_TRUE,
        .dynamicRendering = VK_TRUE,
    };

    VkPhysicalDeviceFeatures2 enabledFeatures{
        .sType = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_FEATURES_2,
        .pNext = &enable13,
    };

    const VkDeviceCreateInfo deviceInfo{
        .sType                   = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO,
        .pNext                   = &enabledFeatures,
        .queueCreateInfoCount    = 1,
        .pQueueCreateInfos       = &queueInfo,
        .enabledExtensionCount   = 1,
        .ppEnabledExtensionNames = deviceExtensions,
        .pEnabledFeatures        = nullptr,   // must be null when using pNext features2
    };

    const VkResult result = vkCreateDevice(m_physicalDevice, &deviceInfo, nullptr, &m_device);
    if (result != VK_SUCCESS)
    {
        return InitializationResult::failure(
            std::format("vkCreateDevice failed: {}", string_VkResult(result)));
    }

    vkGetDeviceQueue(m_device, m_graphicsFamily, 0, &m_graphicsQueue);
    return InitializationResult::success();
}
```

The one rule people trip over: **`pEnabledFeatures` must be `nullptr` if you
chain `VkPhysicalDeviceFeatures2` into `pNext`.** Setting both is a validation
error. `VkPhysicalDeviceFeatures2::features` is where the old 1.0 feature bits
live now.

Note that queues are *retrieved*, not created, and are destroyed with the
device. There is no `vkDestroyQueue`.

---

## 7. What to enable later, and why not now

You will come back to this function several times. Here is the map, so the
returns are quick:

| When | Add to the chain |
| --- | --- |
| Chapter 15 section 5, sharp textures at grazing angles | `VkPhysicalDeviceFeatures::samplerAnisotropy` (in `VkPhysicalDeviceFeatures2::features`), and to the device check, since the spec makes it optional |
| Chapter 15 section 11, the first shader with `discard` | `Vulkan13Features::shaderDemoteToHelperInvocation`; every 1.3 device has it, so no new check |
| Chapter 19, many draws from one indirect call | `VkPhysicalDeviceFeatures::multiDrawIndirect` and `drawIndirectFirstInstance` (in `VkPhysicalDeviceFeatures2::features`, before `samplerAnisotropy` in declaration order), and both to the device check |
| Chapter 33, route B's ray queries | `Vulkan12Features::bufferDeviceAddress` always (Vulkan 1.3 requires it); the extensions `VK_KHR_acceleration_structure`, `VK_KHR_ray_query`, and `VK_KHR_deferred_host_operations` and the features `accelerationStructure` and `rayQuery` only when present (33 §6) |
| Only if you choose `layout(scalar)` (Chapter 08 section 8), which this tutorial does not | `Vulkan12Features::scalarBlockLayout` |
| Only for a faster FFT than the book builds (Chapter 29 section 12) | `Vulkan13Features::subgroupSizeControl` and `computeFullSubgroups` |

Deliberately **not** enabling these now is the point. Every enabled feature is
a hardware requirement, and a path tracer that refuses to launch because you
speculatively enabled ray tracing while writing a triangle is a bad afternoon.

---

## 8. Destruction order

**This is `Shutdown`.** It runs after a successful `Initialize` and after a
failed one, so every handle may still be null — which is why each destroy is
guarded, and why the handles are reset afterwards so a second call is harmless.

```cpp
void VulkanInstance::Shutdown()
{
    if (m_device != VK_NULL_HANDLE)
    {
        // First, and never optional. vkDestroyDevice does NOT wait.
        vkDeviceWaitIdle(m_device);
        vkDestroyDevice(m_device, nullptr);
    }
    if (m_surface != VK_NULL_HANDLE)
    {
        vkDestroySurfaceKHR(m_instance, m_surface, nullptr);
    }
    if (m_messenger != VK_NULL_HANDLE)
    {
        // An extension entry point, so loaded exactly like its create
        // counterpart in section 3.
        auto destroyMessenger = reinterpret_cast<PFN_vkDestroyDebugUtilsMessengerEXT>(
            vkGetInstanceProcAddr(m_instance, "vkDestroyDebugUtilsMessengerEXT"));
        if (destroyMessenger != nullptr) { destroyMessenger(m_instance, m_messenger, nullptr); }
    }
    if (m_instance != VK_NULL_HANDLE)
    {
        vkDestroyInstance(m_instance, nullptr);
    }

    m_device         = VK_NULL_HANDLE;
    m_graphicsQueue  = VK_NULL_HANDLE;
    m_physicalDevice = VK_NULL_HANDLE;
    m_surface        = VK_NULL_HANDLE;
    m_messenger      = VK_NULL_HANDLE;
    m_instance       = VK_NULL_HANDLE;
}
```

`vkDestroyDevice` does **not** wait for outstanding work, which is why
`vkDeviceWaitIdle` leads. That single line prevents most shutdown validation
errors, and it is the first thing to check when you get "cannot destroy X, it is
in use by command buffer Y". (`vkDeviceWaitIdle` on a null device is itself
invalid, which is the other reason for the guard.)

ROADMAP's stated order — debug panels, then Vulkan objects, then surface, then
window — is correct. Keep it.

---

## Exit check

**Now:** regenerate, then build Debug and Release with no errors or warnings.
This chapter's code is compiled into `PillowFortEngine`, though nothing calls
it yet.

**After Chapter 05**, whose `main` is the first code to call `Initialize`, come
back and run the rest:

- [ ] Startup prints the selected GPU name and driver version.
- [ ] The messenger is proven live: temporarily comment out `vkDestroyDevice`
      in `Shutdown`. Debug should report the leaked `VkDevice` at
      `vkDestroyInstance` — and, if you run under the debugger, stop on
      `PF_DEBUG_BREAK`. (The messenger only forwards warnings and errors, so
      silence during a correct run proves nothing. If the leak goes
      unreported, the layer is not loading — check `VK_LAYER_PATH`.)
- [ ] Shutdown produces no validation errors.
- [ ] A missing layer is handled both ways it can happen. Change the name passed
      to `isLayerAvailable`: startup warns and runs without validation.
      Change only the name in `layers.push_back`: the loader reports the
      missing layer through the messenger, then startup fails with
      `vkCreateInstance failed: VK_ERROR_LAYER_NOT_PRESENT` — readable, not a
      crash.
- [ ] Temporarily raising the requirement to `VK_MAKE_API_VERSION(0, 1, 99, 0)`
      in `rejectionReason` fails startup with a message that names your GPU and
      gives its rejection reason. (A version no driver reports, so the check
      fails on every machine. The reason still reads "no Vulkan 1.3", because
      that string is fixed — what you are testing is that it reaches the log.)
- [ ] With two GPUs, `--gpu` plus part of either name (Chapter 05) selects it,
      and a name that matches nothing logs the warning and starts anyway.

Next: [03 — The Swapchain](03-Swapchain.md)
