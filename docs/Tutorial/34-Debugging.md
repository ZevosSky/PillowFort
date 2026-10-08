# 34 — Debugging and Profiling

**Goal:** make the tools tell you what is wrong instead of inferring it from a
black screen.

**ROADMAP:** reference material for every step.

**When to read it:** this chapter is a toolbox, not a step, so it sits last
but is read in pieces. Sections 1-3 are a short RenderDoc walkthrough on this
engine's frame: read them the first time a chapter asks for a capture, which is
Chapter 06's exit check, and come back any time after; section 3 has more to
find once Chapter 10 section 7 adds the per-frame buffer. Section 4 points to
where GPU timing is taught, Chapter 21 section 8, and made a class, Chapter 24
section 9. Sections 5 and 6 are for the first time you need them, section 7 can
be read any time after Chapter 09, and section 8 is the checklist for every
milestone. Nothing here adds code to the engine; section 7's snippets show what
you would write if you chose to.

Everything here is worth doing early. The habit that separates a pleasant
Vulkan project from a miserable one is investing in observability before you
need it, because the moment you need it is the moment you are least able to
build it.

---

## 1. RenderDoc: getting a capture

RenderDoc records every command of one frame, with every resource as it was,
and replays it so you can walk through it: what was bound, what each image
held, what each draw wrote. It is optional: the book asks for it once, in
Chapter 06's exit check, and elsewhere offers it as one way to look. Sections
1-3 follow RenderDoc 1.46's own documentation, applied to this engine;
RenderDoc's own labels are in bold where the text names them.

**Installing.** Get the Windows installer (`.msi`) from renderdoc.org. It also
registers RenderDoc's Vulkan layer, which is how RenderDoc gets inside a Vulkan
program; the layer stays inactive in anything RenderDoc did not launch, and
nothing in the engine changes. If the launch dialog ever warns that Vulkan
capture is not configured, click the warning and RenderDoc registers it.

**vkconfig.** When RenderDoc finds a configuration left by the SDK's
`vkconfig`, it warns that vkconfig has caused problems in the past and
recommends disabling it while you use RenderDoc. Chapter 01 section 5's
override is such a configuration. If you use one, consider turning it off —
select no configuration in `vkconfig` — while you capture.

**A first capture:**

1. Build Debug. Its SPIR-V carries your GLSL source (Chapter 06 section 1's
   `-g`), which section 2 opens.
2. In RenderDoc, choose **File → Launch Application**.
3. **Executable Path**: browse, with the button beside the field, to
   `Build\Artifacts\Debug\SandboxGame\SandboxGame.exe` in your repository.
4. **Working Directory**: leave it empty. RenderDoc then starts the program in
   the executable's folder, and the program finds its shaders and assets beside
   the executable whatever the working directory is (Chapter 06's
   `executableDirectory`, Chapter 13 section 6).
5. **Command-line Arguments**: the options `main` parses, as you would type
   them after `SandboxGame.exe`:
   - `--demo` and part of a demo's name (Chapter 09 section 7);
   - `--gpu` and part of a device's name, and `--present` with `fifo`,
     `fifo-relaxed`, `mailbox`, or `immediate` (Chapter 05 section 3);
   - `--scene` and a file in `Assets/Scenes`, for the USD viewer (Chapter 14
     section 9);
   - `--msaa` and a sample count (Chapter 18 section 3).

   For example, `--demo USD --scene MaterialTest.usda --gpu RTX`. Any
   `debugargs` you added to `premake5.lua` (Chapter 05 section 3, Chapter 09
   section 7) reach only Visual Studio's debugger, so RenderDoc needs its own
   copy here. A `--scene` path with a folder in it is resolved from the working
   directory; give such a path in full.
6. Click **Launch**. The program starts with a small overlay in its top-left
   corner: the API, the frame number, and the capture keys.
7. Press **F12** or **Print Screen** in the program's window. That captures
   the next frame, and the overlay counts it.
8. RenderDoc has opened a window for the running program, and the capture
   appears under **Captures collected**. Double-click it to open it. A capture
   is temporary until you save it, with **File → Save Capture** (Ctrl+S). The
   launch dialog's **Save Settings** keeps the whole setup in a `.cap` file.

**A particular frame.** Before launching, tick **Queue Capture** under
**Actions** and set its frame number, and RenderDoc captures that frame by
itself. For Vulkan, frame 0 runs from the creation of the first `VkDevice` to
the first present, and `main` sets up the starting demo before its first frame.
Queueing frame 0 is therefore how you see work recorded once at setup through
`immediateSubmit` and never again: in a demo with a sky, started with `--demo`,
the image-based lighting's lookup table (Chapter 24 section 7) and the cloud
noise (Chapter 28 section 7).

**A capture is not a validation run.** While RenderDoc is capturing, the
program's own request for the validation layer has no effect, and messages do
not reach Chapter 02's callback: the console stays quiet whatever is wrong, and
`PF_DEBUG_BREAK` never fires. To keep the layer's messages with a capture,
tick **Enable API Validation** among the capture options; RenderDoc stores them
in the capture, where **Window → Errors and Warnings** lists them. Section 5's
messages and section 8's runs come from ordinary runs, outside RenderDoc.
Capturing also changes timing and allocates more memory, and a replay is not a
perfect reproduction, so a bug that depends on timing can vanish under it.

**Two GPUs.** `--gpu` picks the GPU a capture is taken on. Replay uses the
closest match to it RenderDoc can find, or the system default; **File → Open
Capture with Options** has a **GPU Selection Override**. Captures do not carry
between vendors' GPUs, so replay a capture on the GPU that took it.

**What it cannot show.** Ray-tracing work is recorded, and what it writes is
correct afterwards, but the work itself is opaque, by RenderDoc's design. For
Chapter 33's route B, the acceleration structure appears as a binding with a
size, and neither its contents nor the ray queries can be inspected or
debugged. On NVIDIA, Nsight Graphics can; on any GPU, Chapter 33 section 9's
`debugPrintfEXT` reads values from inside a path. On a GPU without the
`accelerationStructureCaptureReplay` feature, RenderDoc 1.46 hides
`VK_KHR_acceleration_structure` from the program, so under capture route B is
not offered and the log says `Ray queries: not on this GPU.`

---

## 2. RenderDoc: reading the frame

Four windows, all under **Window**, carry most of the work: the **Event
Browser**, the **API Inspector**, the **Timeline Bar**, and **Pipeline State**.
RenderDoc shows everything as it stands after the event you select.

**The Event Browser** is the frame as a list. Its **EID** column numbers every
API call in order, and its **Name** column holds the list itself. By default it
shows only *actions*, RenderDoc's word for commands that do work: draws,
dispatches, copies, clears. Binds, push constants, and barriers are not rows of
their own. **Ctrl+F** finds an event, **Ctrl+B** bookmarks one, and
**Ctrl+Left** and **Ctrl+Right** step from action to action.

Without labels (section 7), nothing names the passes. What marks them out is
the `vkCmdBeginRendering` and `vkCmdEndRendering` pair around each rendering
scope, whose names RenderDoc extends with the attachments' load and store
operations, and the compute dispatches between those pairs. Every frame of this
engine has the same two parts:

1. **The demo's part**, everything its `Record` writes into the scene target
   (Chapter 09 section 4). In the triangle, with no arguments, that is one
   scope holding one `vkCmdDraw`. A 3D demo records, in order: the compute that
   feeds the frame, such as the grass's three dispatches (Begin, Generate, End)
   and the copy of its counters, before any rendering; the shadow cascades, one
   depth-only scope each; the scene pass, its color and depth cleared and the
   demo's draws inside; any second scopes over the finished scene, such as the
   USD viewer's light glows; and for the grass, after the scene target is
   handed back, one dispatch per level of its depth pyramid.
2. **The engine's part** (Chapter 08 section 4): one scope on the swapchain
   image, holding the composite's `vkCmdDraw` of three vertices and then
   ImGui's `vkCmdDrawIndexed` calls.

The index's [One 3D frame, in order](../VulkanTutorial.md#one-3d-frame-in-order)
lists every pass the later chapters add. Some appear only on request: the sky,
its bake, the filter of its light, and the clouds are recorded only when the
**Sky** mode is not Off (Chapter 23 section 8), and the bake and the filter only
in a frame in which the sky changed.

**The API Inspector** shows the calls between the previous action and the
selected one, the selected call last, each expandable to its parameters. That is
where binds, push constants, and barriers are read. Synchronization2's
`vkCmdPipelineBarrier2` is not an action, so it never gets a row in the Event
Browser; select the action after it, and expand its `VkDependencyInfo` here to
read every barrier's stages, access masks, and layouts, the three questions of
Chapter 04 section 5. Select the `vkCmdBeginRendering` of the swapchain's
scope, for instance, and the two barriers before it are the scene target's
hand-back to `SHADER_READ_ONLY_OPTIMAL` and the swapchain image's
`UNDEFINED` to `COLOR_ATTACHMENT_OPTIMAL`. Select the composite's draw, and the
calls before it bind its pipeline and set and push its 8 bytes of exposure and
tone curve (Chapter 16 section 6).

**The Timeline Bar** runs in event order, not in time: its sections are not
sized by how long they took. With an image selected in the Texture Viewer, it
marks every event that reads or writes it.

**Durations.** The Event Browser's clock button, **Time durations for the
actions**, times every action and adds a Duration column. Those numbers come
from replaying the capture, on whichever GPU replays it, and capturing changes
timing, so compare them only with each other, within one capture; the engine's
own timestamps (section 4) are the numbers to trust. For occupancy and cache
statistics, the vendors' tools go deeper: Nsight Graphics for NVIDIA, Radeon
GPU Profiler for AMD.

**Pipeline State** shows a row of stages for the selected action: **VTX**,
**VS**, **FS**, **FB**, and the rest, with **CS** for a dispatch. Click a stage
to see what it had bound; section 3 reads those pages. Each shader stage's page
names its shader and opens it in RenderDoc's shader viewer, which is what
Chapter 06's exit check asks for; a Debug build's SPIR-V carries the GLSL
source. Stepping through a shader is a further step: RenderDoc's documentation
ties source-level debugging on Vulkan to `NonSemantic.Shader.DebugInfo.100`
debug information, which glslang writes with `-gVS` and `glslc`'s `-g` does
not, so check what the debugger shows on your build before relying on it.

---

## 3. RenderDoc: finding our buffers

Nothing in this engine has a name RenderDoc can show. Every buffer and image
appears under a generic name, its type and a number (`Buffer` and a number,
`Image` and a number), and the number is RenderDoc's own, not the Vulkan
handle. Section 7 changes that, if you want it. Until then you find a buffer
the way you would in the code, by three things RenderDoc does show:

- **its set and binding**, which are the GLSL's `layout(set = S, binding = B)`;
- **its size**, which is a `sizeof` times a count in the C++ that created it;
- **its usage flags**, in the creation call the **Resource Inspector** shows.

The shaders' side does have names: RenderDoc reads them from the SPIR-V, so a
binding is listed with a name taken from its block, such as `FrameBlock`.

**A mesh draw.** Launch with `--demo USD --scene MaterialTest.usda` and
capture. In the scene pass — the scope whose color target is the window-sized
`R16G16B16A16_SFLOAT` image and whose depth is `D32_SFLOAT`, after any shadow
cascades — select one of the mesh draws, a `vkCmdDrawIndexedIndirect`. Open
**Pipeline State** and click **VS**, then **FS**. Each page lists the bindings
that stage's shader reads (**Show Unused Items** adds the rest): uniform
buffers under **Uniform Buffers**, with the bytes the shader declares, and
everything else under **Resources**, with each buffer's size. What you are
reading is Chapter 08 section 6's descriptor sets, as the later chapters filled
them:

| Binding | What | Size | Stage | From |
| --- | --- | --- | --- | --- |
| set 0, 0 | `FrameData`, a uniform buffer | 368 bytes | VS, FS | Chapter 10 section 7 |
| set 0, 1 | the lights: a 32-byte header and 256 × 80-byte `LightData` | 20,512 bytes | FS | Chapter 16 section 4 |
| set 0, 2 | the instances, 112 bytes each | 114,688 bytes, until it first doubles | VS | Chapter 19 section 3 |
| set 0, 3 | `ShadowData`, a uniform buffer | 336 bytes | FS | Chapter 17 section 6 |
| set 0, 4 | the shadow cascades: 2048 × 2048 `D16_UNORM`, 4 layers | | FS | Chapter 17 section 6 |
| set 0, 10-12 | the sky's light: a 32² cube, a 128² cube with 5 mips, a 64² table | | FS | Chapter 24 section 4 |
| set 1, 0 | `MaterialParameters`, a uniform buffer | 400 bytes | FS | Chapter 15 section 6 |
| set 1, 1-7 | the material's textures, or the 1 × 1 white one in each slot it leaves empty | | FS | Chapter 15 section 7 |

`FrameData` is 368 bytes from Chapter 24 on. It is 224 at Chapter 10 and grows
at Chapters 11, 15, 22, and 24, so its size tells you which version you are
looking at. The sizes in the table are distinct, which is what lets you name
every buffer without names. Each per-frame buffer exists twice, one per frame
in flight (Chapter 04 section 2): a capture binds one of the two, and two
captures may show different numbers for buffers of the same size. The
**Uniform Buffers** table is also a free check of Chapter 08 section 8's rule
that a C++ struct and its GLSL block agree: RenderDoc compares the bytes the
shader declares with the range bound, and marks a binding whose range is short.

**Reading the numbers.** Click the arrow in a binding's **Go** column, or
double-click the row, to open the buffer. A uniform buffer opens with its
members laid out and named from the shader. The **Buffer Viewer** also takes a
format you type, C-like declarations under a packing rule, and reads the bytes
through it when you press **Apply**; that is how you read any buffer the
shader's declaration does not describe the way you want. `FrameData`'s first
fields, under the `std140` rule its GLSL block uses:

```text
#pack(std140)
struct FrameData
{
    mat4  view;
    mat4  projection;
    mat4  viewProjection;
    vec4  cameraPosition;
    float time;
    float deltaTime;
};
FrameData frame;
```

The offsets are `SharedShaderTypes.h`'s: `cameraPosition` at 192, `time` at
208. Two checks need no reference values: `cameraPosition`'s w is 1, and `time`
grows from one capture to the next.

**A compute dispatch.** Launch with `--demo Grass` and select Generate, the
second of the three dispatches at the top of the frame (Chapter 26 section 3).
Its **CS** page has no set 0 at all. The grass's generation shaders (Begin,
Generate, End) declare only set 1, the grass's own set, which they share with
the grass's draws through one pipeline layout; a set number is a position in a
layout, not a count. The depth pyramid's reduce pass has a layout of its own,
with its two bindings in set 0.

| Binding | What | Size |
| --- | --- | --- |
| set 1, 0 | the blades: 48-byte `GrassBlade` × (200,000 + 600,000) | 38,400,000 bytes |
| set 1, 1 | `GrassParameters`, a uniform buffer | 496 bytes |
| set 1, 2 | the tiles: 16 bytes × 4096 | 65,536 bytes |
| set 1, 3 | the counters | 16 bytes |
| set 1, 4 | the two draw commands | 32 bytes |
| set 1, 5 | the depth pyramid: `R32_SFLOAT`, half the window, with mips (Chapter 26 section 9) | |

Each dispatch lists the bindings its own shader uses. A storage buffer opens in
the Buffer Viewer with the shader's declaration filled in, so
`GrassBlade blades[]` becomes a table, one row per blade, which a byte range
narrows and a row offset holds steady from event to event. On End, the third
dispatch, binding 4 holds the two commands End wrote for the frame's two
`vkCmdDrawIndirect` calls (Chapter 19 section 7): vertex counts 15 and 7, the
surviving blades as instance counts, and LOD 1's first instance at 200,000,
where its region of the blade buffer starts.

**Images: the Texture Viewer.** Back on the USD viewer's mesh draw, open the
**Texture Viewer**. Its **Outputs** strip shows what the draw writes, the scene
color target and its depth, and **Inputs** what it reads, the material's
textures and set 0's images. Click a thumbnail to view it.

- The scene target is `R16G16B16A16_SFLOAT` and linear, and its values run
  past 1. The **Range** controls set the black and white points, **Autofit**
  fits them to the image, and the gamma toggle chooses between linear data
  corrected for display and the raw values.
- Depth is cleared to 1, and under a perspective projection most of a scene's
  depth sits close to 1, so the image first looks white; **Autofit** stretches
  what is there.
- Right-click a pixel to pick it. Its value appears in the status bar under the
  image, a UNORM value as a fraction of 1 rather than a byte. The **Pixel
  Context** panel beside it has **History**, every write to that pixel up to
  the selected event, and **Debug**, which opens the shader debugger at that
  pixel.
- The **NaN/INF/-ve Display** overlay paints NaN red, infinity green, and
  negative values blue: the quickest way to find the NaNs section 5 describes.
- The composite's draw is where the frame is encoded: its input is the linear
  scene target, its output the `B8G8R8A8_UNORM` swapchain image it writes sRGB
  into (Chapter 08 section 4). Pick the same pixel in both to see one value
  before and after.
- A dispatch's storage images are among its thumbnails too, so a chain of
  compute passes can be stepped image by image: Chapter 20's Life generations,
  Chapter 29's FFT stages.
- To compare two captures, as Chapter 26 does with occlusion culling on and
  off, save the final image from each with **Save selected Texture** and
  compare the files, or open the second capture from the program's capture
  window in a new RenderDoc instance and view the two side by side.

**Vertices: the Mesh Viewer.** On the same mesh draw, the **Mesh Viewer**
shows the vertex shader's inputs and outputs as tables, **VS Input** and **VS
Output**, beside a preview of the mesh. VS Input's columns come from the
pipeline's vertex input: the shared vertex buffer's 48-byte vertices, position,
normal, uv, and tangent (Chapter 11 section 2, Chapter 19 section 4). The
triangle, the composite, and the grass's blades make their vertices from
`gl_VertexIndex` and have no vertex input, so read VS Output for them.
Right-click a row for **Debug this Vertex**.

**The Resource Inspector** (**Window → Resource Inspector**) lists every object
in the capture. Select one to see the call that created it under **Resource
Initialisation Parameters** — a buffer's `vkCreateBuffer`, with its size and
usage flags — and where the frame uses it under **Usage in Frame**. Bold names
with a link icon, anywhere in RenderDoc, jump here. **Rename Resource** gives
an object a name in RenderDoc alone, saved with the capture: the version of
section 7 that needs no code.

---

## 4. GPU timing with timestamp queries

CPU frame time does not tell you what the GPU spent. Timestamps do: the GPU
writes its own clock into a query pool at points you choose, and you read the
values back once the frame has finished. They are taught where the tutorial
first needs them, **Chapter 21 section 8**: what a timestamp bounds, ticks to
milliseconds through `timestampPeriod`, masking by `timestampValidBits`, one
block of queries per frame in flight, the reset outside a rendering scope, and
reading the results without stalling. **Chapter 24 section 9** makes them the
`GpuTimestamps` class; when you want to time something new, use the class
rather than writing the queries again.

Put the numbers on a panel beside the CPU frame time. Knowing that a pass
costs 1.2 ms of a 6 ms frame changes what you optimize.

---

## 5. Reading validation messages

Messages look intimidating and are highly structured. Take a real one:

```text
Validation Error: [ VUID-vkCmdDraw-None-08114 ]
Object 0: handle = 0x1f2a3b4c, type = VK_OBJECT_TYPE_DESCRIPTOR_SET, name = "Scene.FrameSet"
vkCmdDraw(): the descriptor (VkDescriptorSet 0x1f2a3b4c, set 0, binding 1, index 0)
is being used in draw but has never been updated via vkUpdateDescriptorSets().
```

Read it in three parts:

1. **The VUID** (`VUID-vkCmdDraw-None-08114`) identifies the exact spec
   sentence being violated. Search it to land on that sentence. This is the
   most underused debugging resource in Vulkan. VUIDs are stable enough to
   search but do get renumbered when a rule is rewritten — this one used to be
   `02699` — so if a search finds nothing, search the message text instead.
2. **The objects**, with your names attached, if you gave them any (section 7).
3. **The prose**, which is usually a direct statement of the fix.

Common categories and what they actually mean:

| Message contains | Actual cause |
| --- | --- |
| "has never been updated via vkUpdateDescriptorSets" | Bound a set you allocated but never wrote |
| "is being used ... but has not been ... transitioned" | Wrong image layout for the operation |
| "SYNC-HAZARD-WRITE-AFTER-READ" | Missing barrier. Sync validation. Believe it. |
| "SYNC-HAZARD-READ-AFTER-WRITE" | Missing barrier the other direction |
| "cannot be destroyed ... still in use" | Missing `vkDeviceWaitIdle` before teardown |
| "attachment format ... does not match" | `VkPipelineRenderingCreateInfo` format differs from `VkRenderingInfo` |
| "must be a multiple of ... alignment" | A buffer offset that breaks an alignment limit |
| "Number of currently valid ... objects is not smaller than the maximum" | A leak; you are not destroying something per frame |

**Fix warnings too.** Best-practices warnings are the layer telling you
something is legal but slow. Skim them once per milestone rather than
suppressing them.

**Some mistakes have no message at all.** The layer checks the API's rules,
not what each driver does inside them. A descriptor pool sized for the
descriptors a program writes, rather than for every binding of every set it
allocates (Chapter 24 section 3), is one: NVIDIA's driver and lavapipe let the
pool overfill, AMD's returns `VK_ERROR_OUT_OF_POOL_MEMORY`, and the layer is
silent, because running out of a pool is a runtime error, not a usage error. A
`pow` or `sqrt` of something that is 0 only in exact arithmetic is another: a
GPU's approximate arithmetic can land it a hair below 0, making the result NaN
on the GPU and 0 on lavapipe (Chapter 30 section 6). Section 8's checklist runs
on more than one GPU for these.

---

## 6. When the device is lost

`VK_ERROR_DEVICE_LOST` means the GPU crashed and the driver reset it. On
Windows this is usually TDR — the driver watchdog killed a workload running
longer than about two seconds.

Causes, in order of likelihood for this project:

1. **An infinite or very long loop in a shader.** A path tracer with a
   too-high bounce count, or a `while (rayQueryProceedEXT(...))` that never
   terminates. Try a tiny resolution and a bounce limit of 1.
2. **Out-of-bounds writes.** Turn on GPU-assisted validation; it usually
   catches this precisely.
3. **Bad acceleration structure build.** Misaligned scratch buffer is the
   classic (Chapter 33 section 6).
4. **Genuinely too much work.** A 4K path trace at 64 samples per frame will
   exceed TDR on any GPU. Reduce `samplesPerFrame` and accumulate more frames
   instead.

Narrowing it down:

- **Bisect by disabling passes.** Crude and effective.
- **`VK_EXT_device_fault`** gives you a fault address and vendor-specific
  details after the loss, if the driver supports it.
- **Breadcrumbs.** Write an incrementing marker into a host-visible buffer
  before each pass; after a device loss, the last value written tells you which
  pass died. Ten lines, and it works when nothing else does.
- The TDR timeout is a registry value. Raising it makes debugging a long
  dispatch possible, and it is not something to leave changed.

---

## 7. Names and labels, if you want them

Without them, a validation message names an object by its handle, RenderDoc
shows `Buffer` and a number, and the Event Browser has only the rendering
scopes to go by. `VK_EXT_debug_utils`, the extension Chapter 02 enables for its
messenger, can do better. The reference engine leaves both out by choice, every
listing in the book is shorter for it, and sections 2 and 3 show how much you
can find without them; whether to add them is yours.

**Object names.** `vkSetDebugUtilsObjectNameEXT` attaches a string to a
handle. From then on:

- a validation message names the object beside its handle, as section 5's
  example does with `name = "Scene.FrameSet"`;
- RenderDoc uses the name in place of the generic one everywhere: Pipeline
  State, the Texture Viewer, the Resource Inspector. It keeps one name per
  object per capture, the last one set, so name an object once, when it is
  created.

**Labels.** `vkCmdBeginDebugUtilsLabelEXT` and `vkCmdEndDebugUtilsLabelEXT`
bracket a stretch of a command buffer with a name and a color, and may nest;
`vkCmdInsertDebugUtilsLabelEXT` marks a single point. RenderDoc turns each
begin and end into a collapsible, colored group in the Event Browser, so the
grass's passes or the sea's 48 FFT dispatches become a handful of named groups.
The callback's data has room for the labels open where a message arose,
`pCmdBufLabels`; Chapter 02's callback prints only the message.

**Where they come from.** These are an extension's entry points, so
`vulkan-1.dll` does not export them: calling `vkCmdBeginDebugUtilsLabelEXT`
directly compiles and then fails to link with `LNK2019`. Load them at run time,
the way Chapter 02 section 3 loads the messenger's, with
`vkGetInstanceProcAddr`, which returns any command of an instance extension
that is enabled. The extension is enabled only when validation is (Chapter 02
section 1), so load them under the same condition and leave the pointers null
otherwise:

```cpp
// VulkanInstance, after vkCreateInstance, and only when m_validationEnabled.
m_setObjectName = reinterpret_cast<PFN_vkSetDebugUtilsObjectNameEXT>(
    vkGetInstanceProcAddr(m_instance, "vkSetDebugUtilsObjectNameEXT"));
m_beginLabel = reinterpret_cast<PFN_vkCmdBeginDebugUtilsLabelEXT>(
    vkGetInstanceProcAddr(m_instance, "vkCmdBeginDebugUtilsLabelEXT"));
m_endLabel = reinterpret_cast<PFN_vkCmdEndDebugUtilsLabelEXT>(
    vkGetInstanceProcAddr(m_instance, "vkCmdEndDebugUtilsLabelEXT"));
```

That makes them Debug-only without an `#ifdef`: Release defines no
`PF_VULKAN_VALIDATION`, never enables the extension, and keeps null pointers,
as does a Debug build on a machine without the layer. Every call checks its
pointer and does nothing when it is null, one branch; compile the calls out as
well if you would rather not pay it. Either way, a Release capture has none.

**Where to call them.** Hand the pointers explicitly to whatever creates or
records, as the `VulkanContext` hands out the device; no global. Name an object
right after the call that creates it succeeds, where you know what it is for:
`"FrameData[0]"`, `"Grass.Blades"`, `"Scene.Color"`, with the handle passed as
a `uint64_t` (a `reinterpret_cast` on x64, where every handle is a pointer).
Put labels around each demo's `Record` in `recordFrame`, named by the demo, and
around the composite and ImGui; then, inside the busy demos, around each pass.

```cpp
// VulkanRenderer::recordFrame, before m_demo->Record. A null pointer: the extension is off.
if (m_beginLabel != nullptr)
{
    const VkDebugUtilsLabelEXT label{
        .sType      = VK_STRUCTURE_TYPE_DEBUG_UTILS_LABEL_EXT,
        .pLabelName = m_demo->Name(),
        .color      = { 0.2f, 0.4f, 0.9f, 1.0f },
    };
    m_beginLabel(commandBuffer, &label);
}
```

After `Record`, `m_endLabel(commandBuffer)` closes it, behind the same check.
A label that is begun must be ended on every path out, including an early
`return` added months later; a small class that begins the label in its
constructor and ends it in its destructor makes that automatic.

---

## 8. Checklist before calling a milestone done

Before ticking off any step's exit check:

- [ ] Run Debug with validation and synchronization validation for an extended
      session with no errors.
- [ ] Do it on every GPU you have (`--gpu`, Chapter 05), of more than one
      vendor if you can: section 5's silent mistakes fail on one driver and
      pass on another.
- [ ] Stress resize, minimize, restore, monitor changes, and shutdown.
- [ ] Test the failure paths: a missing `.spv` file and a GPU that does not
      meet requirements should both report, not crash. A missing `glslc` should
      fail the build with a readable error.
- [ ] Delete `Build/` and reproduce Debug and Release from scratch.
- [ ] Rebuild Release from the command line and confirm it is clean.

```powershell
& "C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe" .\Build\Projects\PillowFort.sln /m /p:Configuration=Release /p:Platform=x64
```

---

## Where to go next

By the end of the tutorial you have a Vulkan foundation; a USD scene viewer with
physically based materials, lights, shadows, MSAA, deferred shading, and a sky
that lights it; GPU-driven compute — Life, particles, a grass field, and
clouds; an FFT sea with spray and a floating boat; and a path tracer. The
index's closing page,
[The engine you built](../VulkanTutorial.md#appendix-the-engine-you-built),
draws the whole engine and lists everything the chapters name and do not build.
Three of those are worth doing first:

- **Shader hot reload.** Watch the compiled `.spv` files and rebuild pipelines
  when they change. With sliders already in place, it closes the iteration
  loop. It needs the deletion queue Chapter 06 section 8 describes.
- **The engine's two seams**, before any feature every 3D demo should get: the
  3D demos' shared per-frame code, and set 0 out of `SceneRenderer`.
- **Temporal anti-aliasing**, for what MSAA cannot fix: shading aliasing and the
  grass's sub-pixel blades (Chapter 18 section 9).

Back to the [index](../VulkanTutorial.md).
