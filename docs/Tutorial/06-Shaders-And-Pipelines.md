# 06 — Shaders and Pipelines

**Goal:** a triangle drawn from nothing but `gl_VertexIndex`, compiled to
SPIR-V by the build and loaded from any working directory.

**ROADMAP:** step 7.

**Module:** `VulkanGraphics`, namespace `pf::vulkan_graphics`. The pipeline
objects are `VulkanRenderer` members until Chapter 09 section 6 moves the
triangle into its own demo (ROADMAP step 10).

**Prerequisites:** Chapter 01 section 6 (`glslc` and its flags), Chapter 04's
class map (`VulkanRenderer`, which gains the pipeline), and Chapter 05
section 1 (`recordFrame` and its rendering scope, where the draw goes).

Sections 1-7 are the triangle. Section 8 is for later: Chapter 08 sends you
back to it when the second pipeline arrives.

---

## 1. The shader build

Vulkan consumes SPIR-V, never GLSL, so the build needs a step your C++ compiler
knows nothing about. Each shader stage becomes a **tracked custom-build input**,
MSBuild's name for a file that carries its own command, inputs and outputs:
Premake records the GLSL input, shared includes, command, and SPIR-V output in
the generated project, and MSBuild reruns the command only when an input is
newer than its output. A normal incremental build must notice a shader-only
edit. An untracked prebuild command carries no file-level dependency records:
it can rerun every shader when MSBuild builds the project, while Visual
Studio's fast up-to-date check can skip the project after a shader-only edit.
Premake's [buildinputs](https://premake.github.io/docs/buildinputs/) and
[buildoutputs](https://premake.github.io/docs/buildoutputs/) give the generated
custom-build item the dependency records this path needs.

```lua
-- Above the projects in premake5.lua. Every Name.vert.glsl, Name.frag.glsl, and
-- Name.comp.glsl under Shaders/ is compiled; the stage comes from the name and
-- is passed explicitly, because glslc cannot infer it from .glsl (Chapter 01).
-- Any other .glsl is an include, compiled only through the files that use it.
local shaderStages = { vert = "vertex", frag = "fragment", comp = "compute" }

-- Tracked custom-build inputs keep a shader-only edit visible to MSBuild and
-- Visual Studio's fast up-to-date check. Includes conservatively invalidate all stages.
local function configureShaderBuilds()
    local includes = os.matchfiles("Shaders/**.h")
    for _, file in ipairs(os.matchfiles("Shaders/**.glsl")) do
        if not shaderStages[file:match("%.(%a+)%.glsl$")] then
            table.insert(includes, file)
        end
    end
    for _, file in ipairs(os.matchfiles("Shaders/**.glsl")) do
        local path  = file:match("^Shaders/(.*)%.glsl$")      -- "Triangle/Triangle.vert"
        local stage = shaderStages[path:match("%.(%a+)$")]    -- "vertex"
        if stage then
            local folder = path:match("^(.*)/") or "."
            local output = "%{cfg.targetdir}/Shaders/" .. path .. ".spv"
            filter { "files:" .. file }
                buildmessage ("Compiling shader " .. path)
                buildinputs (includes)
                buildoutputs { output }
            for _, configuration in ipairs({ "Debug", "Release", "Dist" }) do
                local flags = configuration == "Debug" and "-g -O0" or "-O"
                filter { "files:" .. file, "configurations:" .. configuration }
                    buildcommands {
                        '{MKDIR} "%{cfg.targetdir}/Shaders/' .. folder .. '"',
                        '"$(VULKAN_SDK)/Bin/glslc.exe" -fshader-stage=' .. stage ..
                        ' --target-env=vulkan1.3 ' .. flags ..
                        ' -I "%{wks.location}/../../Shaders/Include"' ..
                        ' "%{wks.location}/../../Shaders/' .. path .. '.glsl" -o "' .. output .. '" || exit /b 1'
                    }
            end
        end
    end
    filter {}
end
```

In the existing `SandboxGame` project, include the shader files and call the
helper after the project's ordinary configuration filters have been reset. It
is the executable's project because `%{cfg.targetdir}` must be the folder
`SandboxGame.exe` lands in, which is where section 3 looks for the SPIR-V:

```lua
    files { "Shaders/**.glsl", "Shaders/**.h" }
    configureShaderBuilds()
```

Adding a shader is adding a file, with no shader list maintained by hand.
**Regenerate after adding, moving, or deleting a file**, because Premake
expands those globs and records the dependency set at generation time
(Chapter 01 section 3). Editing an existing stage or include needs only Build.
Debug uses `-g -O0`, unoptimized SPIR-V that carries its GLSL source, which
RenderDoc can show; Release and Dist use `-O`, the SPIR-V optimizer, with no
debug information. `-I` puts `Shaders/Include` on the include path, for the
shared includes Chapter 08 starts. `%{wks.location}` is `Build/Projects`, so
`../../` is the repository root.

The stage file is the custom build's primary input. The include files in
`buildinputs` conservatively invalidate every stage when any shared header
changes, including a demo-local types header. That is deliberately broader
than a compiler dependency scanner, but it cannot silently leave a stale
SPIR-V file. `buildoutputs` records the configuration-specific output so
MSBuild and Visual Studio's up-to-date check can see that work is needed.

Check the contract now: build twice with no changes and see no shader
compilation on the second build. Edit an existing stage, Build, and see its
output recompiled. Edit an include, Build, and see the stages recompiled.
Then undo the edits. Deleting an output and building must also regenerate it.
The complete build definition is [premake5.lua](../../premake5.lua).

Two things to get right while it is still this small:

- **Mirror the source tree in the output path.** Flattening
  `Triangle/Triangle.vert.glsl` down to `Shaders/Triangle.vert.spv` works right
  up until two demos each have a `Common.comp`, at which point one silently
  overwrites the other and you spend an evening debugging the wrong shader.
- **Executable-relative, never working-directory-relative.** Launching from
  Visual Studio, from Explorer, and from a terminal gives you three different
  working directories, and the bug only shows up in one of them. One function
  fixes it permanently.

That function, `executableDirectory`, goes in a new file pair,
`ExecutableFiles.h` and `ExecutableFiles.cpp`, with everything else in this
chapter that reads or writes a file beside the executable — the SPIR-V reader
in section 3 and the pipeline cache in section 6. New files mean regenerating
before the next build:

```cpp
// Source/PillowFort/VulkanGraphics/ExecutableFiles.h, inside namespace pf::vulkan_graphics
// (includes <vulkan/vulkan.h>, <cstdint>, <filesystem>, <vector>)
std::filesystem::path executableDirectory();                                   // below
std::vector<uint32_t> readSpirv(const std::filesystem::path& relativePath);    // section 3
std::vector<char>     loadPipelineCache(const VkPhysicalDeviceProperties& device);   // section 6
void                  savePipelineCache(VkDevice device, VkPipelineCache cache);     // section 6
```

```cpp
// Source/PillowFort/VulkanGraphics/ExecutableFiles.cpp, inside namespace pf::vulkan_graphics.
// Includes <windows.h> for GetModuleFileNameW, plus <fstream>, <iterator>,
// <cstring>, <format>, and Log.h for the functions in sections 3 and 6.
std::filesystem::path executableDirectory()
{
    wchar_t buffer[MAX_PATH];
    const DWORD length = GetModuleFileNameW(nullptr, buffer, MAX_PATH);
    return std::filesystem::path(buffer, buffer + length).parent_path();
}
```

---

## 2. The triangle shaders

A draw runs two programs you write, on the GPU, many times at once:

- The **vertex shader** runs once per vertex. Its job is to say where that
  vertex lands on screen, by writing the built-in `gl_Position`. It can also
  write other outputs, such as a color, for the next stage.
- Between the two, fixed hardware called the **rasterizer** takes each group of
  three vertices as a triangle and finds every pixel it covers. Each covered
  pixel is a **fragment**.
- The **fragment shader** runs once per fragment and writes its color. Its
  inputs are the vertex shader's outputs, **blended across the triangle**: a
  fragment a third of the way from the red corner to the green one receives a
  color two-thirds red and one-third green.

This triangle needs no vertex buffer. The vertex shader gets its corners from a
constant array, indexed by `gl_VertexIndex`, which counts 0, 1, 2 for a
three-vertex draw.

> **Jump:** shader invocations are separate executions, not iterations of a
> C++ loop sharing local variables. Each vertex invocation writes its own
> outputs; the rasterizer interpolates those outputs for fragment invocations.
> The fragment shader receives that interface, not the vertex shader's arrays
> or local variables. Chapter 08 supplies other inputs through push constants
> and descriptors.

The small amount of **GLSL** needed for this attempt resembles C++:
`vec2`, `vec3`, and `vec4` hold two, three, and four floating-point components;
`vec4(aVec3, 1.0)` appends a fourth component. An `out` declares a value this
stage writes; an `in` declares one it receives. Matching `layout(location = 0)`
declarations connect the color between stages; the fragment output at location
0 instead names color attachment 0. A location connects interfaces, not two
variables sharing CPU memory.

**The screen-coordinate convention differs from OpenGL's**, in two ways that
matter from Chapter 10 on. With our positive-height viewport, **Y points down**,
so `-0.5` is above center. And **depth after dividing by `w` runs `[0, 1]`**,
not `[-1, 1]`. The vertex shader writes *clip coordinates*; dividing their
`x`, `y`, and `z` by `w` gives *normalized device coordinates*. Here `w = 1`,
so the two have the same numbers. GLM assumes OpenGL's conventions, so Chapter 10 section 2 flips Y
in its projection matrix, and the `GLM_FORCE_DEPTH_ZERO_TO_ONE` define in
Chapter 01's `premake5.lua` makes GLM produce `[0, 1]` depth. That define, like
every `GLM_FORCE_*` switch, lives once there and never as a `#define` above an
include: two files that disagree compile two versions of the same inline
function, and the linker silently keeps one.

<a id="ch06-triangle"></a>

**Attempt CH06-triangle: hand a color from one shader to the other.** Write
the vertex and fragment shaders before opening the answer. A three-vertex
draw, with no vertex buffers, must put a red corner at `(0, -0.5)`, green at
`(0.5, 0.5)` and blue at `(-0.5, 0.5)`. Use depth 0 and `w = 1`. The interior
must blend the three colors rather than show three flat regions. Explain
which stage chooses the corner and which stage receives an interpolated
color. Compile both with section 1's shader build; after sections 3-7, check
the triangle's orientation and gradient on screen.

**Acceptance:** The specified corners and orientation render with a smoothly interpolated RGB interior; both shaders compile with their matching interface.

**Transfer:** Swap two corner positions but keep their color assignments. Predict the winding and gradient change before rendering with the same pipeline.

<details>
<summary>Hint 1: an invocation writes one corner</summary>

`gl_VertexIndex` selects the position and color. An output of the vertex
shader becomes an interpolated input to the fragment shader; the fragment
shader does not need to know which corner started it.

</details>

<details>
<summary>Hint 2: give the two stages a matching interface</summary>

Use two three-element constant arrays in the vertex shader, one for positions
and one for RGB colors. Give the color output and input the same location.
The fragment shader writes that input into its color attachment output.

</details>

<details>
<summary>Hint 3: distinguish built-ins from declared varyings</summary>

Both files start with `#version 450`. `gl_Position` and `gl_VertexIndex` are
built-ins; declare `layout(location = 0) out vec3 fragmentColor` in the vertex
shader and the matching `in` in the fragment shader. The fragment's output is
a `vec4` with alpha 1.

</details>

<details>
<summary>Worked solution: the triangle's two shaders</summary>

```glsl
// Shaders/Triangle/Triangle.vert.glsl
#version 450

layout(location = 0) out vec3 fragmentColor;

const vec2 positions[3] = vec2[](
    vec2( 0.0, -0.5),
    vec2( 0.5,  0.5),
    vec2(-0.5,  0.5)
);

const vec3 colors[3] = vec3[](
    vec3(1.0, 0.0, 0.0),
    vec3(0.0, 1.0, 0.0),
    vec3(0.0, 0.0, 1.0)
);

void main()
{
    gl_Position   = vec4(positions[gl_VertexIndex], 0.0, 1.0);
    fragmentColor = colors[gl_VertexIndex];
}
```

```glsl
// Shaders/Triangle/Triangle.frag.glsl
#version 450

layout(location = 0) in  vec3 fragmentColor;
layout(location = 0) out vec4 outColor;

void main()
{
    outColor = vec4(fragmentColor, 1.0);
}
```

`gl_Position` has four clip coordinates, `(x, y, z, w)`. Since `w = 1` here,
`x` and `y` also give the normalized -1 to 1 range across the window, whatever
its size in pixels. Depth is 0 here; Chapter 10 section 2 explains the divide
when a camera supplies other values of `w`. This is where the triangle's
corners land:

```text
         x = -1           x = 0          x = +1
   y = -1   ┌───────────────────────────────┐
            │                               │
            │               ● (0, -0.5) red │
            │                               │
   y =  0   │               +               │
            │                               │
            │        ●             ●        │
            │   (-0.5, 0.5)    (0.5, 0.5)   │
            │       blue         green      │
   y = +1   └───────────────────────────────┘
```

The fragment shader's `fragmentColor` is the blend of the three corner colors,
which is why the triangle shows a gradient rather than three flat colors.

The shaders as the repository ends up with them are
[Triangle.vert.glsl](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Shaders/Triangle/Triangle.vert.glsl) and
[Triangle.frag.glsl](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Shaders/Triangle/Triangle.frag.glsl); the fragment
shader there has grown Chapter 08's push constants and color decode.

</details>

### Written now, used in Chapter 08: the fullscreen triangle

The same trick covers the whole window with no vertex buffer: one triangle big
enough that the screen fits inside it. Chapter 08's composite pass draws the
offscreen image to the screen this way, and Chapter 09's gradient demo reuses
it. It is three lines, so it goes in now, beside the triangle:

```glsl
// Shaders/Fullscreen/Fullscreen.vert.glsl
#version 450

layout(location = 0) out vec2 uv;

void main()
{
    // vertexIndex 0 -> (0,0), 1 -> (2,0), 2 -> (0,2)
    uv = vec2((gl_VertexIndex << 1) & 2, gl_VertexIndex & 2);
    gl_Position = vec4(uv * 2.0 - 1.0, 0.0, 1.0);
}
```

The bit operations give the three vertices `uv` = (0, 0), (2, 0) and (0, 2),
so `uv * 2 - 1` puts the corners at (-1, -1), (3, -1) and (-1, 3). The long
edge passes exactly through the window's bottom-right corner (1, 1), and inside
the window `uv` runs from (0, 0) at the top-left to (1, 1) at the bottom-right:
the same corners as an image's texture coordinates, which is why Chapter 08's
composite can sample with `uv` directly.

Draw with `vkCmdDraw(cmd, 3, 1, 0, 0)`. One oversized triangle is measurably
faster than two triangles forming a quad, because the quad's diagonal makes
every 2x2 pixel block along it shade twice. (GPUs shade pixels in 2x2 blocks;
Chapter 15 section 5 says why.)

---

## 3. Shader modules

First, getting the SPIR-V off disk. SPIR-V is a stream of 32-bit words, so it
is read into `uint32_t`s, in `ExecutableFiles.cpp` beside
`executableDirectory`. A missing file is reported, not asserted, per the
roadmap; the caller sees an empty vector:

```cpp
std::vector<uint32_t> readSpirv(const std::filesystem::path& relativePath)
{
    const std::filesystem::path path = executableDirectory() / "Shaders" / relativePath;

    std::ifstream file(path, std::ios::binary | std::ios::ate);
    if (!file)
    {
        // u8string, not string(): on Windows, string() converts to the ANSI code
        // page and throws for any character outside it, so this log would crash.
        Log::error(std::format("Shader not found: {}",
                               reinterpret_cast<const char*>(path.u8string().c_str())).c_str());
        return {};
    }

    const std::streamsize bytes = file.tellg();
    if (bytes <= 0 || bytes % static_cast<std::streamsize>(sizeof(uint32_t)) != 0)
    {
        Log::error(std::format("Not a SPIR-V file ({} bytes): {}", bytes,
                               reinterpret_cast<const char*>(path.u8string().c_str())).c_str());
        return {};
    }

    std::vector<uint32_t> words(static_cast<size_t>(bytes) / sizeof(uint32_t));
    file.seekg(0);
    if (!file.read(reinterpret_cast<char*>(words.data()), bytes))
    {
        Log::error(std::format("Reading SPIR-V failed: {}",
                               reinterpret_cast<const char*>(path.u8string().c_str())).c_str());
        return {};
    }
    return words;
}
```

Then the module. A `VkShaderModule` is the device's handle for one SPIR-V
blob, and section 4's pipeline names one per stage. An empty vector is not a
valid module (`codeSize` must be greater than 0), so the caller checks
`readSpirv`'s result before calling this (section 7 says where):

```cpp
// File scope, above the namespace block in VulkanRenderer.cpp. Needs nothing
// from the class. Section 8 moves it into GraphicsPipeline.cpp.
static VkShaderModule createShaderModule(VkDevice device, const std::vector<uint32_t>& spirv)
{
    const VkShaderModuleCreateInfo moduleInfo{
        .sType    = VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO,
        .codeSize = spirv.size() * sizeof(uint32_t),   // BYTES
        .pCode    = spirv.data(),
    };

    VkShaderModule module = VK_NULL_HANDLE;
    const VkResult result = vkCreateShaderModule(device, &moduleInfo, nullptr, &module);
    if (result != VK_SUCCESS)
    {
        Log::error(std::format("vkCreateShaderModule failed: {}", string_VkResult(result)).c_str());
        return VK_NULL_HANDLE;
    }
    return module;
}
```

Two rules behind the helper:

- **`codeSize` is in bytes, `pCode` is `uint32_t*`.** Read into a
  `std::vector<uint32_t>` and the size arithmetic stays honest; a
  `std::vector<char>` needs a cast at every use and a `size()` that means bytes in
  one line and words in the next, which is where the off-by-four comes from.
- **Shader modules are consumed at pipeline creation.** Destroy them
  immediately after `vkCreateGraphicsPipelines` returns. Keeping them alive is a
  common leak, and there is nothing to keep them alive for.

Check each returned module before making the pipeline. If the vertex module
fails, return an `InitializationResult::failure`; if the fragment module fails,
destroy the successful vertex module first, then return failure. A failed
Vulkan create does not give you an owned object to destroy. The helper logs
the driver result and returns the known null value instead of publishing the
failed output.

---

## 4. The graphics pipeline

**This is `createTrianglePipeline`**, a new private `VulkanRenderer` function
(section 7 lists what lands where). It reads both shaders with `readSpirv`,
makes their modules with `createShaderModule`, creates section 5's layout, and
then fills in the create-infos below.

Almost all fixed-function state — what the hardware does around the shaders:
assembling triangles, rasterizing, blending — is immutable and baked in here.
That is the trade: you pay for one big object up front, and in exchange the
driver compiles the shaders together with that state once, so a draw does no
hidden shader recompiling or driver-side state validation.

Each create-info below configures one step of the path a draw takes. In
order, with the field that holds each:

```text
 vkCmdDraw(3 vertices)
        ▼
 vertex input         pVertexInputState     where vertices come from: nothing yet (Chapter 11)
 input assembly       pInputAssemblyState   every three vertices make a triangle
        ▼
 VERTEX SHADER        pStages[0]            once per vertex: writes gl_Position
        ▼
 viewport, scissor    pViewportState        clip space to pixels; set each frame
 rasterization        pRasterizationState   culling, front face; finds the covered pixels
 multisample          pMultisampleState     one sample per pixel until Chapter 18
        ▼
 FRAGMENT SHADER      pStages[1]            once per fragment: writes outColor
        ▼
 depth test           pDepthStencilState    none until Chapter 10
 color blend          pColorBlendState      off: the fragment replaces the pixel
        ▼
 color attachment     VkPipelineRenderingCreateInfo   only its format, here
```

```cpp
const VkPipelineShaderStageCreateInfo stages[] = {
    { .sType  = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,
      .stage  = VK_SHADER_STAGE_VERTEX_BIT,
      .module = vertexModule,
      .pName  = "main" },
    { .sType  = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,
      .stage  = VK_SHADER_STAGE_FRAGMENT_BIT,
      .module = fragmentModule,
      .pName  = "main" },
};

// No vertex buffers: the shader generates positions from gl_VertexIndex.
const VkPipelineVertexInputStateCreateInfo vertexInput{
    .sType = VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO,
};

const VkPipelineInputAssemblyStateCreateInfo inputAssembly{
    .sType    = VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO,
    .topology = VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST,
};

// Counts must be 1 even though the values come from vkCmdSetViewport.
const VkPipelineViewportStateCreateInfo viewportState{
    .sType         = VK_STRUCTURE_TYPE_PIPELINE_VIEWPORT_STATE_CREATE_INFO,
    .viewportCount = 1,
    .scissorCount  = 1,
};

const VkPipelineRasterizationStateCreateInfo rasterization{
    .sType       = VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_STATE_CREATE_INFO,
    .polygonMode = VK_POLYGON_MODE_FILL,
    .cullMode    = VK_CULL_MODE_NONE,          // see note below
    .frontFace   = VK_FRONT_FACE_CLOCKWISE,       // matches the vertex order above, Y down
    .lineWidth   = 1.0f,                       // must be 1.0 unless wideLines is enabled
};

const VkPipelineMultisampleStateCreateInfo multisample{
    .sType                = VK_STRUCTURE_TYPE_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO,
    .rasterizationSamples = VK_SAMPLE_COUNT_1_BIT,
};

const VkPipelineColorBlendAttachmentState blendAttachment{
    .blendEnable    = VK_FALSE,
    .colorWriteMask = VK_COLOR_COMPONENT_R_BIT | VK_COLOR_COMPONENT_G_BIT
                    | VK_COLOR_COMPONENT_B_BIT | VK_COLOR_COMPONENT_A_BIT,
};

const VkPipelineColorBlendStateCreateInfo colorBlend{
    .sType           = VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO,
    .attachmentCount = 1,
    .pAttachments    = &blendAttachment,
};

const VkDynamicState dynamicStates[] = {
    VK_DYNAMIC_STATE_VIEWPORT,
    VK_DYNAMIC_STATE_SCISSOR,
};

const VkPipelineDynamicStateCreateInfo dynamicState{
    .sType             = VK_STRUCTURE_TYPE_PIPELINE_DYNAMIC_STATE_CREATE_INFO,
    .dynamicStateCount = 2,
    .pDynamicStates    = dynamicStates,
};

// Dynamic rendering: describe attachment FORMATS instead of a VkRenderPass.
const VkFormat colorFormat = m_swapchain.format();
const VkPipelineRenderingCreateInfo renderingInfo{
    .sType                   = VK_STRUCTURE_TYPE_PIPELINE_RENDERING_CREATE_INFO,
    .colorAttachmentCount    = 1,
    .pColorAttachmentFormats = &colorFormat,
    .depthAttachmentFormat   = VK_FORMAT_UNDEFINED,
    .stencilAttachmentFormat = VK_FORMAT_UNDEFINED,
};

const VkGraphicsPipelineCreateInfo pipelineInfo{
    .sType               = VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO,
    .pNext               = &renderingInfo,
    .stageCount          = 2,
    .pStages             = stages,
    .pVertexInputState   = &vertexInput,
    .pInputAssemblyState = &inputAssembly,
    .pViewportState      = &viewportState,
    .pRasterizationState = &rasterization,
    .pMultisampleState   = &multisample,
    .pDepthStencilState  = nullptr,
    .pColorBlendState    = &colorBlend,
    .pDynamicState       = &dynamicState,
    .layout              = m_pipelineLayout,
    .renderPass          = VK_NULL_HANDLE,   // dynamic rendering
    .subpass             = 0,
};

VkPipeline pipeline = VK_NULL_HANDLE;
const VkResult pipelineResult = vkCreateGraphicsPipelines(m_device, m_pipelineCache, 1, &pipelineInfo, nullptr, &pipeline);
vkDestroyShaderModule(m_device, vertexModule, nullptr);
vkDestroyShaderModule(m_device, fragmentModule, nullptr);
if (pipelineResult != VK_SUCCESS)
{
    return InitializationResult::failure(
        std::format("vkCreateGraphicsPipelines failed: {}", string_VkResult(pipelineResult)));
}
m_pipeline = pipeline;
```

### Things worth knowing rather than copying

**`VkPipelineRenderingCreateInfo` replaces the render pass entirely.** The
pipeline needs to know attachment *formats* to compile the fragment output, not
a render pass object. This means **your pipeline survives swapchain
recreation** as long as the format is unchanged — and the format only changes
if the surface itself changed, which is rare. A render-pass pipeline survives a
resize too, since it needs only a compatible render pass; what dynamic
rendering removes is the `VkRenderPass` object and the per-image
`VkFramebuffer`s that every resize had to rebuild, which is its real win here.

**Dynamic viewport and scissor are not optional in practice.** Without them,
every resize rebuilds every pipeline. With them, you call
`vkCmdSetViewport`/`vkCmdSetScissor` each frame and nothing else changes. Note
that `viewportCount` and `scissorCount` must still be 1 in the create info even
though the values are dynamic.

**No viewport flip.** A negative viewport height would also turn Vulkan's Y-down
into OpenGL's Y-up. It is not wrong, but it is a second place to flip: flip in
both and the two cancel, so the image comes out upside down and every mesh
winds the opposite way to what `frontFace` expects, the classic cause of
inside-out models. This tutorial keeps the
viewport positive and flips once, in the projection matrix (Chapter 10
section 2).

**`cullMode = NONE` for now.** With `CULL_MODE_BACK_BIT`, a triangle wound the
wrong way vanishes entirely, and "nothing renders" has too many possible causes
at this stage. Turn culling on once you can see the triangle.

`frontFace` has to describe the vertices you actually wrote. Top-center, then
bottom-right, then bottom-left runs clockwise on screen in Vulkan's Y-down
framebuffer, so `FRONT_FACE_CLOCKWISE` is what makes the triangle front-facing
— `COUNTER_CLOCKWISE`, the OpenGL habit, would make culling remove it. The
fullscreen triangle from section 2 is clockwise too.

---

## 5. Pipeline layout

Even with nothing to bind, you need a layout: a complete graphics pipeline's
`layout` must be a valid handle, and the layout is where Chapter 08 declares
push constants and descriptor sets. It is created before section 4's pipeline,
which names it:

```cpp
const VkPipelineLayoutCreateInfo layoutInfo{
    .sType                  = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
    .setLayoutCount         = 0,
    .pushConstantRangeCount = 0,
};
VkPipelineLayout layout = VK_NULL_HANDLE;
const VkResult layoutResult = vkCreatePipelineLayout(m_device, &layoutInfo, nullptr, &layout);
if (layoutResult != VK_SUCCESS)
{
    return InitializationResult::failure(
        std::format("vkCreatePipelineLayout failed: {}", string_VkResult(layoutResult)));
}
m_pipelineLayout = layout;
```

---

## 6. Pipeline cache

Building a pipeline compiles its shaders into the GPU's own machine code, and
a driver can spend a noticeable fraction of a second on each one. The triangle
compiles instantly, but from Chapter 10 on the program builds many pipelines on
every launch, while you relaunch constantly. A `VkPipelineCache` keeps the
compiled results, and saving it to a file beside the executable lets the next
launch skip the work. It is a five-minute job now.

**The short version first.** An empty cache is all the triangle needs, and it is
one struct. **This is `initialize`**, before any pipeline:

```cpp
const VkPipelineCacheCreateInfo cacheInfo{
    .sType = VK_STRUCTURE_TYPE_PIPELINE_CACHE_CREATE_INFO,   // empty: nothing saved yet
};
VkPipelineCache cache = VK_NULL_HANDLE;
const VkResult cacheResult = vkCreatePipelineCache(m_device, &cacheInfo, nullptr, &cache);
if (cacheResult != VK_SUCCESS)
{
    return InitializationResult::failure(
        std::format("vkCreatePipelineCache failed: {}", string_VkResult(cacheResult)));
}
m_pipelineCache = cache;
```

With that, go on to section 7 and get the triangle on screen; come back for the
rest of this section afterwards. **Keeping the cache across launches** fills
`pInitialData` from a file, and writes the file back at shutdown. The create
becomes:

```cpp
VkPhysicalDeviceProperties properties{};
vkGetPhysicalDeviceProperties(m_vulkan.PhysicalDevice(), &properties);
const std::vector<char> previousCacheBlob = loadPipelineCache(properties);   // may be empty

const VkPipelineCacheCreateInfo cacheInfo{
    .sType           = VK_STRUCTURE_TYPE_PIPELINE_CACHE_CREATE_INFO,
    .initialDataSize = previousCacheBlob.size(),
    .pInitialData    = previousCacheBlob.data(),
};
VkPipelineCache cache = VK_NULL_HANDLE;
const VkResult cacheResult = vkCreatePipelineCache(m_device, &cacheInfo, nullptr, &cache);
if (cacheResult != VK_SUCCESS)
{
    return InitializationResult::failure(
        std::format("vkCreatePipelineCache failed: {}", string_VkResult(cacheResult)));
}
m_pipelineCache = cache;
```

The two file functions live in `ExecutableFiles.cpp`. Add `<array>`, `<span>`,
`<cstring>`, `<format>` and `<fstream>` to its includes, plus
`<vulkan/vk_enum_string_helper.h>` for result names; its existing `<windows.h>`
provides the same-directory file replacement. The application envelope below
is separate from the opaque Vulkan blob: only the payload goes into
`VkPipelineCacheCreateInfo`.

```cpp
// This application envelope is not passed to Vulkan. It catches a truncated or
// corrupted disk write before the driver sees the opaque bytes inside it.
static constexpr uint64_t CACHE_MAGIC = 0x3145484341434650ull; // "PFCACHE1"
static constexpr uint64_t CACHE_VERSION = 1;
static constexpr uint64_t MAX_CACHE_BYTES = 512ull * 1024 * 1024;

static uint64_t cacheChecksum(std::span<const char> bytes)
{
    uint64_t hash = 14695981039346656037ull;
    for (unsigned char value : bytes) { hash = (hash ^ value) * 1099511628211ull; }
    return hash;
}

static std::vector<char> loadPipelineCacheFile(const std::filesystem::path& path,
                                               const VkPhysicalDeviceProperties& device)
{
    std::ifstream file(path, std::ios::binary | std::ios::ate);
    if (!file) { return {}; }
    const std::streamoff length = file.tellg();
    std::array<uint64_t, 4> envelope{};
    if (length < static_cast<std::streamoff>(sizeof(envelope) + sizeof(VkPipelineCacheHeaderVersionOne))) { return {}; }
    file.seekg(0);
    if (!file.read(reinterpret_cast<char*>(envelope.data()), sizeof(envelope))) { return {}; }
    const uint64_t payloadSize = static_cast<uint64_t>(length) - sizeof(envelope);
    if (envelope[0] != CACHE_MAGIC || envelope[1] != CACHE_VERSION || envelope[2] != payloadSize
        || payloadSize > MAX_CACHE_BYTES) { return {}; }
    std::vector<char> blob(static_cast<size_t>(payloadSize));
    if (!file.read(blob.data(), static_cast<std::streamsize>(blob.size())) || cacheChecksum(blob) != envelope[3]) { return {}; }

    VkPipelineCacheHeaderVersionOne header{};
    std::memcpy(&header, blob.data(), sizeof(header));

    const bool matches = header.headerSize == sizeof(header)
                      && header.headerVersion == VK_PIPELINE_CACHE_HEADER_VERSION_ONE
                      && header.vendorID      == device.vendorID
                      && header.deviceID      == device.deviceID
                      && std::memcmp(header.pipelineCacheUUID, device.pipelineCacheUUID,
                                     VK_UUID_SIZE) == 0;
    return matches ? blob : std::vector<char>{};
}

static bool savePipelineCacheFile(const std::filesystem::path& path, VkDevice device, VkPipelineCache cache)
{
    if (cache == VK_NULL_HANDLE) { return true; }   // initialization failed before creating it

    size_t size = 0;
    VkResult result = vkGetPipelineCacheData(device, cache, &size, nullptr);
    if (result != VK_SUCCESS || size < sizeof(VkPipelineCacheHeaderVersionOne) || size > MAX_CACHE_BYTES)
    {
        Log::warning(std::format("Pipeline cache size query failed or returned an invalid size: {}", string_VkResult(result)).c_str());
        return false;
    }
    std::vector<char> blob(size);
    result = vkGetPipelineCacheData(device, cache, &size, blob.data());
    if (result != VK_SUCCESS || size < sizeof(VkPipelineCacheHeaderVersionOne) || size > blob.size())
    {
        Log::warning(std::format("Pipeline cache readback failed; previous file retained: {}", string_VkResult(result)).c_str());
        return false;
    }
    blob.resize(size);

    auto temporary = path;
    temporary += "." + std::to_string(GetCurrentProcessId()) + ".tmp";
    std::ofstream file(temporary, std::ios::binary | std::ios::trunc);
    const std::array<uint64_t, 4> envelope{ CACHE_MAGIC, CACHE_VERSION, blob.size(), cacheChecksum(blob) };
    file.write(reinterpret_cast<const char*>(envelope.data()), sizeof(envelope));
    file.write(blob.data(), static_cast<std::streamsize>(blob.size()));
    file.close();
    const bool saved = bool(file) && MoveFileExW(temporary.c_str(), path.c_str(),
                                               MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH) != 0;
    if (!saved)
    {
        std::error_code ignored;
        std::filesystem::remove(temporary, ignored);
        Log::warning("Saving the pipeline cache failed; previous file retained.");
    }
    return saved;
}

// Missing, legacy raw, incompatible or damaged files produce a cold cache.
std::vector<char> loadPipelineCache(const VkPhysicalDeviceProperties& device)
{
    return loadPipelineCacheFile(executableDirectory() / "pipeline_cache.bin", device);
}

// Called from shutdown, after vkDeviceWaitIdle and before vkDestroyPipelineCache.
void savePipelineCache(VkDevice device, VkPipelineCache cache)
{
    (void)savePipelineCacheFile(executableDirectory() / "pipeline_cache.bin", device, cache);
}
```

**Why both headers.** The Vulkan header identifies the GPU and driver through
its IDs and cache UUID. Our envelope adds a version, exact payload size and
checksum, so a truncated or accidentally corrupted file is rejected before
its opaque bytes reach the driver. Legacy raw cache files start cold once;
missing or rejected cache data does not change rendering.

**Why a temporary file.** Both `vkGetPipelineCacheData` calls must succeed
before writing. The save closes and checks a file beside the destination,
then uses `MoveFileExW` with replacement enabled. A readback, write or rename
failure leaves the previous cache in place and logs a warning. `VK_INCOMPLETE`
can return a valid partial blob, but this shutdown path deliberately retains
the previous complete file instead. One cache file still means switching
between GPUs starts cold; naming it per device is a later optimization.

---
## 7. Drawing

**This is `recordFrame`**, inside Chapter 05's rendering scope. The begin and
end lines are Chapter 05's, shown to place the four new calls between them;
`renderingInfo` there is Chapter 05's `VkRenderingInfo`, not section 4's
`VkPipelineRenderingCreateInfo` of the same name:

```cpp
vkCmdBeginRendering(commandBuffer, &renderingInfo);

const VkExtent2D extent = m_swapchain.extent();
const VkViewport viewport{ 0.0f, 0.0f,
                           static_cast<float>(extent.width),
                           static_cast<float>(extent.height),
                           0.0f, 1.0f };
const VkRect2D scissor{ { 0, 0 }, extent };

vkCmdSetViewport(commandBuffer, 0, 1, &viewport);
vkCmdSetScissor(commandBuffer, 0, 1, &scissor);

vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, m_pipeline);
vkCmdDraw(commandBuffer, 3, 1, 0, 0);   // 3 vertices, 1 instance

vkCmdEndRendering(commandBuffer);
```

`vkCmdDraw(commandBuffer, 3, 1, 0, 0)` runs the vertex shader three times with
`gl_VertexIndex` of 0, 1, 2. There are no buffers and no bindings. This is the
smallest complete Vulkan draw there is.

### Where this lands in `VulkanRenderer`

Everything in this chapter is a `VulkanRenderer` member until Chapter 09
section 6 moves the triangle into its own demo: a `VkPipelineCache m_pipelineCache`
(section 6), a `VkPipelineLayout m_pipelineLayout` (section 5), and a
`VkPipeline m_pipeline` (section 4), all `VK_NULL_HANDLE` until created.
`initialize` creates them after the swapchain, since the pipeline needs its
format: the cache, then the layout and the pipeline in a private
`createTrianglePipeline()`, which makes its two shader modules just before
`vkCreateGraphicsPipelines` and destroys them right after (`VulkanRenderer.cpp`
includes `ExecutableFiles.h` for `readSpirv` and the cache). The snippets
above show only the create calls. `createTrianglePipeline` returns an
`InitializationResult`, like Chapter 04's `createFrameResources`: an empty
`readSpirv` result, or a layout or pipeline create that does not return
`VK_SUCCESS`, fails `initialize` with a message. Chapter 09 section 6's
`TriangleDemo::Setup` keeps that shape. `shutdown` destroys the
three in reverse, after `vkDeviceWaitIdle` and before the swapchain, with
`savePipelineCache` ahead of `vkDestroyPipelineCache`. Every `initialize` line
needs its `shutdown` line, or Chapter 02's exit check, "Shutdown produces no
validation errors", stops passing: `vkDestroyDevice` reports every object
still alive.

---

## 8. When the second pipeline arrives

**Skip this section on a first reading.** For now the triangle's pipeline stays
written out as in section 4: the roadmap's rule is to write a pattern twice
before generalizing it. The second time comes in Chapter 08, when the composite
pass needs a fullscreen pipeline into the swapchain format while the triangle's
moves to the offscreen format, and Chapter 08 sends you back here. That is the
moment to make pipelines configurable, and there are two levers.

**First, move state out of the pipeline.** Vulkan 1.3 made a long list of
states dynamic in core, with no feature bit to check: cull mode, front face,
primitive topology (within one class — triangles stay triangles), depth test,
depth write, depth compare op, stencil test and ops, depth bias enable,
rasterizer discard, primitive restart, and viewport and scissor *with count*.
Declare them in `pDynamicStates`, set them with `vkCmdSet*` at record time, and
they stop being reasons to build a second pipeline. What stays baked in is
short: the shaders, the vertex input layout, the attachment formats, blending,
polygon mode, sample count, and the layout.

**Then describe what is left as data.** A plain aggregate with defaults, filled
with designated initializers — the same style as every create-info in this
tutorial, and still plain Vulkan types rather than an abstraction over them:

```cpp
// Source/PillowFort/VulkanGraphics/GraphicsPipeline.h
enum class BlendMode { Opaque, Alpha, Additive };

struct GraphicsPipelineDesc
{
    std::filesystem::path       vertexShader;     // relative to executableDirectory()/Shaders
    std::filesystem::path       fragmentShader;
    std::span<const VkFormat>   colorFormats;
    VkFormat                    depthFormat  = VK_FORMAT_UNDEFINED;
    bool                        depthTest    = false;   // Chapter 10's depth buffer turns these on
    bool                        depthWrite   = false;
    VkCompareOp                 depthCompare = VK_COMPARE_OP_LESS;
    BlendMode                   blend        = BlendMode::Opaque;
    const VkSpecializationInfo* fragmentSpecialization = nullptr;   // Chapter 08's encodeSrgb
    VkPipelineLayout            layout       = VK_NULL_HANDLE;
};
```

With a `depthFormat` set, the function must pass a
`VkPipelineDepthStencilStateCreateInfo` built from the three depth fields;
section 4's `pDepthStencilState = nullptr` is only valid with no depth
attachment. The depth fields and `fragmentSpecialization` go beyond what the
triangle needs because the next two pipelines need them: Chapter 08's
composite pass has a specialization constant, and Chapter 10's cubes test
depth. `blend` maps `Opaque` to section 4's `blendEnable = VK_FALSE`; `Alpha` to
source factor `SRC_ALPHA` and destination `ONE_MINUS_SRC_ALPHA`
(`color * a + destination * (1 - a)`); and `Additive` to `ONE` and `ONE`
(`color + destination`). Both blended modes keep alpha's own factors at `ONE`
and `ZERO`. No desc asks for blending until Chapter 21's particles. Chapter 11
grows the desc once more, with vertex input, culling, and extra dynamic state,
when meshes arrive.

One function turns a desc into a pipeline:

```cpp
// Source/PillowFort/VulkanGraphics/GraphicsPipeline.h, beside the desc.
// VK_NULL_HANDLE, logged, if a shader is missing or creation fails.
VkPipeline createGraphicsPipeline(VkDevice device, VkPipelineCache cache,
                                  const GraphicsPipelineDesc& desc);
```

Its body, in `GraphicsPipeline.cpp`, is section 4's struct literals with the
desc's fields substituted, plus `readSpirv` and `createShaderModule` — which
moves there from `VulkanRenderer.cpp`, since this is now its only caller. A
call site then reads as what makes this pipeline different, and nothing else:

```cpp
const VkFormat hdrFormat = VK_FORMAT_R16G16B16A16_SFLOAT;
const GraphicsPipelineDesc triangle{
    .vertexShader   = "Triangle/Triangle.vert.spv",
    .fragmentShader = "Triangle/Triangle.frag.spv",
    .colorFormats   = { &hdrFormat, 1 },
    .layout         = m_pipelineLayout,
};
```

Two things to leave for later, deliberately. Pipeline layouts stay written by
hand per pipeline; generating them from SPIR-V reflection is the automation to
consider after the third. And changing a pipeline *at runtime* — a wireframe
toggle, shader hot reload — means destroying one that an in-flight frame may
still be using. For a rare change the simple answer is to wait:
`vkDeviceWaitIdle`, then destroy. That wait can hitch while outstanding work
finishes. Frequent replacement can instead defer destruction in a small queue.
Stop recording the old handle; submit already-recorded uses and
include them in the completion proof, or reset those command buffers before
reuse (or discard them without submitting).
Retire the object only after every submitted use has completed
([pipeline lifetime](https://docs.vulkan.org/refpages/latest/refpages/source/vkDestroyPipeline.html)).
A frame-slot queue can collect entries after its fence wait only when that
wait covers all those uses, including work on other queues if added later.
Counting CPU frames alone does not establish completion. ROADMAP defers hot
reload; the deletion queue arrives with it.

---

## If nothing appears

In rough order of likelihood:

| Symptom | Likely cause |
| --- | --- |
| Clear color shows, no triangle | Culling on with the wrong winding, or `vkCmdSetViewport` not called with dynamic state declared |
| Validation: format mismatch | `VkPipelineRenderingCreateInfo::pColorAttachmentFormats` does not match the swapchain format |
| Validation: pipeline not bound | No `vkCmdBindPipeline` since `vkBeginCommandBuffer`, or it was bound at the compute bind point. (Binding outside a rendering scope is legal and the binding carries into it.) |
| SPIR-V parse error | `codeSize` in `uint32_t` units instead of bytes |
| Shader file not found | Working-directory-relative path; resolve against `executableDirectory()` |
| Triangle upside down | Something is flipping Y — a negative viewport height, or a projection with `[1][1]` negated. The shader's positions are already written for Vulkan's Y-down, so it should point up with neither. |

---

## Exit check

<details>
<summary>Optional visual reference: inspect orientation and clear margins</summary>

![The assembled reference's upward-pointing triangle, surrounded by red clear color.](images/reference-triangle.png)

Find the top vertex and the horizontal lower edge. This retained image is
from assembled checkpoint `1729bea`; its later shader controls change the
colors, so compare orientation and clear margins. The
[capture notes](ReferenceImages.md#orient-the-first-draws) record its source
and settings. Your resize and launch-path checks below establish more than
this one frame can show.

</details>

- [ ] After regenerating (new shaders and new `ExecutableFiles` sources),
      building emits all three `.spv` files under the executable's directory,
      mirroring their source folders.
- [ ] Break a shader with a syntax error and build. MSBuild must fail (normally
      `MSB8066`), even if another stage compiles successfully afterwards. Restore
      it and rebuild before running; a stale `.spv` is not a successful compile.
- [ ] The triangle renders when launched from Visual Studio, from Explorer, and
      from a terminal — three different working directories, one correct path.
- [ ] The triangle renders and survives resize without pipeline recreation.
- [ ] Debug SPIR-V shows readable source in RenderDoc: capture a frame, select
      the draw, and open the vertex shader from Pipeline State. (Chapter 34
      sections 1-3 walk through RenderDoc, from taking the capture to Pipeline
      State; read them now if RenderDoc is new to you.)

Next: [07 — ImGui Debug Panels](07-ImGui.md)
