# 34 — Debugging and Profiling

**Goal:** make the tools tell you what is wrong instead of inferring it from a
black screen.

**ROADMAP:** reference material for every step.

**When to read it:** this chapter is a toolbox, not a step, so it sits after
the core chapters but is read in pieces. Sections 1-3 are a short RenderDoc
walkthrough on this engine's frame: read them the first time a chapter asks for
a capture, which is Chapter 06's exit check, and come back any time after. At
Chapter 06 the triangle is all there is to capture: use the early route below
and sections 1-2's viewer controls, rather than expecting the later passes.
Section 3's exercise reads the USD viewer at Chapter 24's state,
its Deferred path (Chapter 22) and the grass (Chapter 26), so return to it once
you have those. Sections 4-7 are for the first time you need them, and
section 8 is the checklist for every milestone. Nothing here adds code to the
engine.

Everything here is worth doing early. The habit that separates a pleasant
Vulkan project from a miserable one is investing in observability before you
need it, because the moment you need it is the moment you are least able to
build it.

---

<a id="early-capture-route"></a>

**Use the capture that matches what you have built.** The resource walkthrough
later in this chapter describes a developed renderer. These earlier stopping
points each give you a complete, smaller inspection:

| Your stage | Select and inspect | What establishes success |
| --- | --- | --- |
| Chapter 06 | The triangle's `vkCmdDraw`, its VS/FS pages and color output | The triangle's shaders and three generated vertices write the swapchain image. There is no camera uniform, scene target or composite pass yet |
| Chapter 08 | The triangle draw into the HDR target, then the composite's full-screen draw | The composite's sampled image is the same HDR image the triangle wrote; the composite outputs the swapchain image |
| Chapter 10 | A cube draw's VS page, set 0 binding 0 | Its `FrameData` block is 224 bytes at this stage. Read `cameraPosition` at offset 192; move the camera, capture again, and check the field changes |
| Chapters 19-24 | A USD mesh draw, then the composite | Use section 3's full access-chain exercise; lighting/IBL bindings require the chapters named in its table |

At Chapter 06, leave later `--demo` and `--scene` arguments out of the launch
dialog. Their parsers have not been written. Come back to section 3's grass
dispatch example after Chapters 26-27; a missing future buffer is not a
capture failure.

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
5. **Command-line Arguments**: the options the chapters teach `main` to
   parse, as you would type them after `SandboxGame.exe`: `--demo`
   (Chapter 09 section 7), `--gpu` and `--present` (Chapter 05 section 3),
   `--scene` (Chapter 14 section 9), and `--msaa` (Chapter 18 section 3). For
   example,
   `--demo USD --scene MaterialTest.usda --gpu RTX`. Any `debugargs` you added
   to `premake5.lua` (Chapter 05 section 3) reach only Visual Studio's
   debugger, so RenderDoc needs its own copy here. A `--scene` path with a
   folder in it is resolved from the working directory; give such a path in full.
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
Capture with Options** has a **GPU Selection Override**. Vulkan capture
portability is limited by features and resource choices recorded on the capture
hardware; the override does not guarantee a different GPU can replay it. Start
with the capture GPU; [RenderDoc 1.46's feature notes](https://github.com/baldurk/renderdoc/blob/v1.46/docs/getting_started/features.rst#vulkan)
describe the need for sufficiently comparable hardware.

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
operations, and the compute dispatches between those pairs. From Chapter 09 on,
the chapter-stage frame has two parts; at Chapter 06, inspect the single
triangle scope described in the early route:

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
`vkCmdPipelineBarrier2` is not an action, so by default it gets no row in
the Event Browser; select the action after it, and expand its
`VkDependencyInfo` here to read every barrier's stages, access masks, and
layouts, the three questions of Chapter 04 section 5. Select the `vkCmdBeginRendering` of the swapchain's
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
timing, so compare them within the same replay configuration. The engine's own
timestamps (section 4) describe its live marker intervals; check their scope
and repeat controlled comparisons before attributing a change to one pass.
For occupancy and cache
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

**Stage sizes versus the current reference.** The tables below describe the
Chapter 24 viewer and the Chapter 27 standalone grass (including Chapter 26's
optional depth pyramid). Later chapters extend both. In the assembled
`reference-main`, [the shared header](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Shaders/Include/SharedShaderTypes.h)
declares `FrameData` as 416 bytes (Chapter 51 adds 16 after convergence's
400); `MaterialParameters` remains 400. [The grass header](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Shaders/Grass/GrassTypes.h)
declares 80-byte `GrassBlade`, 592-byte `GrassParameters` and 32-byte
`GrassCounters`; its command buffer holds three 16-byte commands, including
captured clumps. Those are different stages, not evidence of a packing bug.
Use the shader declarations and current `sizeof` assertions for your capture.
Locate Generate by its compute shader and bindings, not by its ordinal among
all dispatches: the sky and later renderer refinements add work too.

<a id="ch34-capture"></a>

**Attempt CH34-capture: identify resources from the frame's evidence.** Use
sections 1-2 to capture the USD viewer on `MaterialTest.usda`. Before opening
the walkthrough below, locate a mesh draw, its frame constants, its instance
buffer and the texture supplying its base color. For each, record the event,
shader stage, set and binding, and size or format. Then locate the composite
draw and identify the image that connects the mesh rendering to it. A correct
answer is a chain of accesses you can point to in the capture, not only a
resource with a plausible name. The worked solution traces this specific
frame. General Buffer, Texture and Mesh Viewer and Resource Inspector guidance
remains visible after that answer, so another chapter can link directly to it.

**Acceptance:** The capture records form a concrete mesh-to-composite access chain, including event, stage, set/binding and resource size/format.

**Transfer:** Switch the USD viewer's panel to **Deferred** and capture the same scene again at 1x, the only sample count the deferred path runs at (Chapter 22 section 9). Predict the added attachments and lighting dispatch, then identify which composite input stays the final lit scene.

<details>
<summary>Hint 1: start at the consumer</summary>

Select a draw or dispatch, then inspect the resources its active shaders
actually read. Work backward from those bindings to their sizes and creation
parameters. Names help, but the bound handle and access are the evidence.

</details>

<details>
<summary>Hint 2: follow the scene image across passes</summary>

Find the window-sized HDR color target and the final full-screen draw that
samples it into the swapchain. On Forward the mesh shader lights directly;
on Deferred the G-buffer pass is followed by compute lighting. Both feed the
same composite input.

</details>

<details>
<summary>Hint 3: use Pipeline State and the Resource Inspector together</summary>

Inspect VS and FS bindings on `vkCmdDrawIndexedIndirect`, using Show Unused
Items only when you need to distinguish a layout from its current readers.
The Resource Inspector provides creation flags and Usage in Frame. Match the
vertex stride and shared struct sizes to the code, rather than relying on
RenderDoc's numbered resource names.

</details>

<details>
<summary>Worked solution: tracing a mesh frame's resources</summary>

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

`FrameData` is 368 bytes from Chapter 24 until the convergence checkpoint after
Chapter 39, which appends 32 bytes of haze and makes it 400. Chapter 51 grows
it to the current 416. It is 224 at Chapter 10 and grows at Chapters 11, 15,
22, and 24, so its size tells you which version you are looking at. Bindings
5-9 are missing on purpose: Chapter 22's lighting set reuses set 0's numbers
and puts its own images there. Of set 1's textures, binding 1 is the base
color (`baseColorTexture` in `MaterialSet.glsl`). The sizes in the table are
distinct, which is what lets you name every buffer without names; from the
convergence checkpoint until Chapter 51, `FrameData` and `MaterialParameters`
are both 400 bytes, and the set number and block name tell them apart. Each
per-frame buffer exists twice, one per frame in flight
(Chapter 04 section 2): a capture binds one of the two, and two captures may
show different numbers for buffers of the same size. The
**Uniform Buffers** table is also a free check of Chapter 08 section 8's rule
that a C++ struct and its GLSL block agree: RenderDoc compares the bytes the
shader declares with the range bound, and marks a binding whose range is short.

</details>

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
  what is there. Horizon reverses depth, so there it first looks black instead.
  Chapter 35's local workaround clears to 0 after the sky; the assembled
  `DepthConvention` path clears to 0 at the pass's start, as its
  [later-stage note](35-Seeing-Far.md) explains.
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

**Forward against Deferred.** With the panel on **Deferred** at 1x, the scene
pass becomes the G-buffer pass: the same mesh draws, now into four color
attachments, the scene target first and then the G-buffer's
`R8G8B8A8_SRGB` base color, `R16G16_SFLOAT` normal, and `R8G8B8A8_UNORM`
surface images (Chapter 22 section 2). After it comes one new dispatch, the
lighting pass (Chapter 22 section 6), with a layout of its own: its set 0
repeats bindings 0, 1, 3, and 4 under the same numbers, puts the three
G-buffer images and the depth at 5-8 and the sky's specular cube at 11, and
binds the scene target at 9 as a storage image in `GENERAL`, which the pass
reads and rewrites. The composite's input does not change: it is still the
scene target, now holding what the lighting pass wrote.

---

## 4. GPU timing with timestamp queries

CPU frame time does not tell you what the GPU spent. Timestamps do: the GPU
writes its own clock into a query pool at points you choose, and you read the
values back once the frame has finished. They are taught where the tutorial
first needs them, **Chapter 21 section 8**: the timestamp's synchronization scopes, ticks to
milliseconds through `timestampPeriod`, masking by `timestampValidBits`, one
block of queries per frame in flight, the reset outside a rendering scope, and
reading the results without stalling. **Chapter 24 section 9** makes them the
`GpuTimestamps` class; when you want to time something new, use the class
rather than writing the queries again.

Put the intervals on a panel beside CPU frame time. First identify the commands
between each pair of markers: a label can include setup, copies or conditional
sky work. A marker's dependency waits for earlier work but ends at its write;
barriers between passes do not make each difference an exclusive pass cost.
Use repeated comparisons with the same GPU and workload to choose a region
to investigate, then a GPU profiler for deeper attribution. Chapter 21's
small dependency counterexample explains why this distinction matters.

---

## 5. Reading validation messages

Messages look intimidating and are highly structured. Take this one, from a
build that names its objects (section 7); this engine names none, so its
messages show only the handle:

```text
Validation Error: [ VUID-vkCmdDraw-None-08114 ]
Object 0: handle = 0x1f2a3b4c, type = VK_OBJECT_TYPE_DESCRIPTOR_SET, name = "Scene.FrameSet"
vkCmdDraw(): the descriptor (VkDescriptorSet 0x1f2a3b4c, set 0, binding 1, index 0)
is being used in draw but has never been updated via vkUpdateDescriptorSets().
```

<a id="ch34-validation"></a>

**Attempt CH34-validation: turn a message into a checked diagnosis.** Before
opening the interpretation, name the operation, set, binding and violated
condition in this message. Find the allocation, descriptor write and bind
that should connect that resource to the draw. Propose two ways the condition
could arise and the evidence that distinguishes them; do not assume the
allocation failed merely because the draw reports an invalid descriptor.
A useful diagnosis identifies the first broken connection and the call that
would repair it, and explains when rewriting that descriptor is safe. The
worked solution also holds this section's general reference: how to read any
message, a table of common ones, and the mistakes that produce none.

**Acceptance:** The diagnosis identifies the violated condition, first broken connection, repair call and safe rewrite timing using descriptor history.

**Transfer:** Assume the same valid write targets a different descriptor set than the draw binds. Predict the evidence distinguishing that case from an omitted write, then trace both handles.

<details>
<summary>Hint 1: separate the rule from the object reporting it</summary>

The VUID identifies a Vulkan rule; the handle and binding identify this
instance of the problem. The prose states what was invalid at the draw.
Trace that descriptor's history, rather than treating the draw as its creator.

</details>

<details>
<summary>Hint 2: compare the set that was written with the set that was bound</summary>

A missing write and a correct write to a different set can produce the same
message. Check the allocated set, `dstSet` and `dstBinding` of the write,
and the set number and handle of the bind. A write after the draw is recorded
does not repair it either: updating a set that a command buffer in the
recording or executable state has bound invalidates that command buffer,
unless the binding was created update-after-bind.

</details>

<details>
<summary>Hint 3: rule out a lifetime race before rewriting</summary>

The message says set 0, binding 1, index 0 was never updated. Initialization
can write it before any frame uses it; a later repair needs the same
no-in-flight-reader guarantee as Chapter 08 section 6. Do not rewrite a set
already bound by a command buffer you intend to submit.

</details>

<details>
<summary>Worked solution: reading and investigating validation messages</summary>

Read it in three parts:

1. **The VUID** (`VUID-vkCmdDraw-None-08114`) identifies the exact spec
   sentence being violated. Search the Vulkan specification for it to land on
   that sentence. This is the
   most underused debugging resource in Vulkan. VUIDs are stable enough to
   search but do get renumbered when a rule is rewritten — this one used to be
   `02699` — so if a search finds nothing, search the message text instead.
2. **The objects**, with your names attached, if you gave them any (section 7).
3. **The prose**, which is usually a direct statement of the fix.

For this message, the operation is `vkCmdDraw`, the resource is set 0,
binding 1, array element 0, and the broken condition is an unwritten
descriptor. In this renderer that binding is the light storage buffer from
Chapter 16, and the `vkCmdDraw` that reads it is the USD viewer's light glows,
six vertices per light. The mesh draws read it too and, in Chapter 19's
default Multi-draw mode, would report the same rule as
`VUID-vkCmdDrawIndexedIndirect-None-08114`: the middle of a VUID names the
command. An absent write to binding 1 means initialization omitted it;
a write whose `dstSet` differs from the handle bound at the draw means the
wrong set was written or bound. Check those handles in the initialization
and recording paths before changing the draw. Write the correct storage
buffer descriptor before its first use, or bind the correctly initialized
set for the frame slot. If repairing a running frame, first establish that
neither an in-flight submission nor a command buffer you will submit uses
the set. Allocating another set alone cannot repair its missing contents.

</details>

Common categories and what they actually mean:

| Message contains | Actual cause |
| --- | --- |
| "has never been updated via vkUpdateDescriptorSets" | Bound a set you allocated but never wrote |
| "is being used ... but has not been ... transitioned" | Wrong image layout for the operation |
| "SYNC-HAZARD-WRITE-AFTER-READ" | A write not ordered after an earlier read: the barrier is missing, or its source stage misses the reader. Sync validation. Believe it. |
| "SYNC-HAZARD-READ-AFTER-WRITE" | A read not ordered after an earlier write, or the write never made visible: the barrier is missing, or its source stage or access misses the writer |
| "SYNC-HAZARD-WRITE-AFTER-WRITE" | Two writes not ordered, where a layout transition counts as a write: Chapter 05's positive control |
| "cannot be destroyed ... still in use" | Destroyed while a submission may still use it: wait for that frame slot's fence, or defer the destroy (Chapter 06 section 8); `vkDeviceWaitIdle` before teardown |
| "attachment format ... does not match" | `VkPipelineRenderingCreateInfo` format differs from `VkRenderingInfo` |
| "must be a multiple of ... alignment" | A buffer offset that breaks an alignment limit |
| "Number of currently valid ... objects is not smaller than the maximum" | A leak; you are not destroying something per frame |

**Fix warnings too.** Best-practices warnings are the layer telling you
something is legal but slow. This engine never asks for them: Chapter 02's
`enables` setting lists only synchronization validation. Switch them on for a
run, with **Best Practices** in vkconfig (Chapter 01 section 5, whose warning
about overrides applies) or by adding
`VK_VALIDATION_FEATURE_ENABLE_BEST_PRACTICES_EXT` to that list, and skim them
once per milestone rather than suppressing them.

**Some mistakes have no message at all.** The layer checks API contracts;
it cannot establish the application's numerical intent. Budget a descriptor
pool for every binding of every allocated set, rather than only the bindings
the program writes (Chapter 24 section 3). Likewise, `pow` or `sqrt` inputs
that reach a domain boundary only in exact arithmetic need floating-point
range checks (Chapter 30 section 6). The driver comparisons reported in those
chapters motivate Section 8's checks on more than one GPU; they are not
vendor-wide promises about current implementations.

Synchronization-validation coverage also depends on the layer and settings.
Chapter 20 section 5's table records **layer 1.4.363** observations, including
missed atomic writes and descriptor-array reads. Keep that version with the
result, consult the [current SyncVal limitations](https://github.com/KhronosGroup/Vulkan-ValidationLayers/blob/main/docs/syncval_usage.md),
and use a matching positive control for your installation. An item absent
from today's limitation list does not prove the old case is fixed. Derive a
barrier from Chapter 04's producer/consumer questions; silence alone does not
supply that argument.

---

## 6. When the device is lost

`VK_ERROR_DEVICE_LOST` reports a lost logical or physical device; it does not
identify the cause or prove that a driver reset occurred. Timeouts, invalid
application work, platform resource events, implementation errors and hardware
faults are possible causes. See Vulkan's
[Lost Device contract](https://docs.vulkan.org/spec/latest/chapters/devsandqueues.html#devsandqueues-lost-device).
On Windows, [TDR](https://learn.microsoft.com/en-us/windows-hardware/drivers/display/timeout-detection-and-recovery)
is one timeout/recovery mechanism. Its default two-second
threshold concerns completing or preempting a GPU task, not a portable
two-second budget for every dispatch.

Start with these hypotheses; a return code alone does not rank them:

1. **An infinite or very long loop in a shader.** A path tracer with a
   too-high bounce count, or a `while (rayQueryProceedEXT(...))` that never
   terminates. Try a tiny resolution and a bounce limit of 1.
2. **Out-of-bounds writes.** Turn on GPU-assisted validation
   (`VK_LAYER_GPUAV_ENABLE=1` for one run, as Chapter 19's exit check does, or
   vkconfig's GPU-AV, Chapter 01 section 5). An instrumented shader-access
   report can locate a bad access; no report does not establish memory safety.
3. **Bad acceleration structure build.** Misaligned scratch buffer is the
   classic (Chapter 33 section 6).
4. **Genuinely too much work.** A path trace at 4K with many samples per
   frame can outlast the watchdog, which is why Chapter 33's **Samples per
   frame** slider stops at 16 and clamps typed values too. Reduce
   `samplesPerFrame` and accumulate more frames instead.

Narrowing it down:

- **Bisect by disabling passes.** Crude and effective.
- **`VK_EXT_device_fault`** gives you a fault address and vendor-specific
  details after the loss, if the driver supports it and the device was
  created with the extension and its `deviceFault` feature enabled; this
  engine enables neither.
- **Execution breadcrumbs need a supported diagnostic path.** A CPU log before
  recording a pass shows recording progress, not GPU completion. Ordinary
  GPU-written mapped memory has undefined contents after device loss under
  Vulkan's contract; its last visible number is not a portable crash locator.
  Where supported and enabled, a facility such as
  [`VK_NV_device_diagnostic_checkpoints`](https://docs.vulkan.org/spec/latest/chapters/debugging.html#debugging-device-loss)
  reports execution checkpoints through its dedicated post-loss query.
  Checkpoints bound observed progress at supported stages; they do not prove
  which later instruction caused the loss. This engine does not enable them.
- **Keep the reproduction bounded.** Reduce resolution, samples, bounces and
  enabled passes while preserving the failing case. Microsoft's
  [TDR registry controls](https://learn.microsoft.com/en-us/windows-hardware/drivers/display/tdr-registry-keys)
  are for targeted driver-development testing, not an application workaround.

After loss, stop normal frame submission and report the failure. The existing
logical device cannot be reset to a healthy state; recovery requires rebuilding
device-owned resources on a new device if creation succeeds. Child objects
still need orderly destruction. This tutorial reports and exits rather than
implementing that recovery system.

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
section 1), so load them under the same condition, one
`vkGetInstanceProcAddr` call per entry point after `vkCreateInstance`, and
leave the pointers null otherwise.

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
Put labels around each demo's `Record` in `recordFrame`, named by the demo
(`Name()`), with a color, and around the composite and ImGui; then, inside the
busy demos, around each pass. A label is begun before the stretch it names and
ended after it, both behind the same null check. A label that is begun must be
ended on every path out, including an early `return` added months later; a
small class that begins the label in its constructor and ends it in its
destructor makes that automatic.

---

## 8. Checklist before calling a milestone done

Before ticking off any step's exit check:

- [ ] Run Debug with validation and synchronization validation for a bounded
      session covering the chapter's exit checks, after Chapter 05's positive control has fired:
      a quiet layer is evidence only once it has shown it can speak.
- [ ] Do it on every GPU you have (`--gpu`, Chapter 05), of more than one
      vendor if you can: section 5's silent mistakes fail on one driver and
      pass on another.
- [ ] Exercise resize, minimize, restore, monitor changes, and shutdown in a
      bounded lifecycle run.
- [ ] Test the failure paths: a missing `.spv` file and a GPU that does not
      meet requirements should both report, not crash. A missing `glslc` should
      fail the build with a readable error.
- [ ] Reproduce Debug and Release from a clean checkout with regenerated
      projects. Keep the diagnostic receipts from the original checkout.
- [ ] Rebuild Release from the command line and confirm it is clean.

```powershell
& "C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe" .\Build\Projects\PillowFort.sln /m:1 /nr:false /p:CL_MPCount=1 /p:UseMultiToolTask=true /p:MultiProcMaxCount=1 /p:EnforceProcessCountAcrossBuilds=true /p:Configuration=Release /p:Platform=x64
```

---

## Where to go next

The index's closing page,
[The engine you built](../VulkanTutorial.md#appendix-the-engine-you-built),
draws the whole engine and lists everything the chapters name and do not build.
Two of those are worth doing first: shader hot reload, which closes the
iteration loop and needs the deletion queue of Chapter 06 section 8; and
temporal anti-aliasing, for what MSAA cannot fix (Chapter 18 section 9). The
shared frame construction and set-0 owner (`makeFrameData`, `FrameBindings`)
are introduced in Chapter 10. Chapter 39's separate convergence exercises
strengthen geometry ownership, visibility/depth and failed-frame submission;
they do not ask you to extract those frame helpers again.

Next: [35 — Seeing Far](35-Seeing-Far.md), beginning the written far-view arc
35-41, then 43. Wind (42) and surf (44) remain planned. The independent
[scene-project chapter (45)](45-Scene-Documents-And-Properties.md) can be read
after 19. Or return to the [routes](../VulkanTutorial.md#chapters).
