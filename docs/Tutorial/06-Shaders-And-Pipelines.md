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
knows nothing about. The roadmap says exactly what that step is: **compile with
`glslc` as a premake prebuild command, write the `.spv` beside the executable,
and resolve it relative to the executable.** That is the whole mechanism.

```lua
-- Above the projects in premake5.lua. Every Name.vert.glsl, Name.frag.glsl, and
-- Name.comp.glsl under Shaders/ is compiled; the stage comes from the name and
-- is passed explicitly, because glslc cannot infer it from .glsl (Chapter 01).
-- Any other .glsl is an include, compiled only through the files that use it.
local shaderStages = { vert = "vertex", frag = "fragment", comp = "compute" }

-- Builds the prebuild command list for one set of glslc flags.
local function shaderCommands(flags)
    local commands = {}
    for _, file in ipairs(os.matchfiles("Shaders/**.glsl")) do
        local path  = file:match("^Shaders/(.*)%.glsl$")      -- "Triangle/Triangle.vert"
        local stage = shaderStages[path:match("%.(%a+)$")]    -- "vertex"
        if stage then
            local folder = path:match("^(.*)/") or "."
            table.insert(commands, '{MKDIR} "%{cfg.targetdir}/Shaders/' .. folder .. '"')
            table.insert(commands,
                '"$(VULKAN_SDK)/Bin/glslc.exe" -fshader-stage=' .. stage ..
                ' --target-env=vulkan1.3 ' .. flags ..
                ' -I "%{wks.location}/../../Shaders/Include"' ..
                ' "%{wks.location}/../../Shaders/' .. path .. '.glsl"' ..
                ' -o "%{cfg.targetdir}/Shaders/' .. path .. '.spv"')
        end
    end
    return commands
end
```

```lua
project "SandboxGame"
    -- ...
    filter "configurations:Debug"
        prebuildcommands(shaderCommands("-g -O0"))   -- readable GLSL in RenderDoc
    filter "configurations:not Debug"
        prebuildcommands(shaderCommands("-O"))
    filter {}
```

Adding a shader is adding a file — no edit to `premake5.lua`, which is what
ROADMAP step 10's "a new demo touches only its own folder" needs once demos bring
their own shaders (Chapter 09 section 8 adds the second demo that way). The
glob runs at generation time, exactly like the C++ ones, so **after adding a
shader, rerun `GenerateProjects.bat`**. The flags split by
configuration for the reason Chapter 01 gave: `-g -O0` keeps names and line
information so RenderDoc shows your GLSL (Chapter 34 section 2 says what
stepping through it needs), and Release wants the optimizer instead.

It recompiles every shader on every build, which for a dozen small shaders costs
well under a second. That is fine, and it stays fine for longer than you expect.

One catch, because the step is invisible to Visual Studio: the IDE's
up-to-date check only knows about the C++ sources, so after editing *only* a
shader it can decide the project needs no build and skip the prebuild step with
it. If a shader edit does not show up, that is why — build from the command
line, or Rebuild. (A per-file custom build rule would let MSBuild track each
shader and its includes; this project does not need one yet.)

Two things to get right while it is still this small:

- **Mirror the source tree in the output path.** Flattening
  `Triangle/Triangle.vert.glsl` down to `Shaders/Triangle.vert.spv` works right
  up until two demos each have a `Common.comp`, at which point one silently
  overwrites the other and you spend an evening debugging the wrong shader.
- **Executable-relative, never working-directory-relative.** Launching from
  Visual Studio, from Explorer, and from a terminal gives you three different
  working directories, and the bug only shows up in one of them. One function
  fixes it permanently.

It lives with everything else in this chapter that reads or writes a file
beside the executable — the SPIR-V reader in section 3 and the pipeline cache
in section 6:

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
three-vertex draw:

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

`gl_Position` has four numbers, `(x, y, depth, w)`. `x` and `y` are in **clip
space**: -1 to 1 across the window, whatever its size in pixels. Depth is 0
here, and `w` is 1; Chapter 10 section 2 gives both their meaning, when a
camera arrives. This is where the triangle's corners land:

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

**Vulkan's clip space is not OpenGL's**, in two ways that matter from Chapter
10 on. **Y points down**, so `-0.5` is above center. And **depth runs `[0, 1]`**,
not `[-1, 1]`. GLM assumes OpenGL's conventions; Chapter 10 section 2 flips Y
in its projection matrix, and the `GLM_FORCE_DEPTH_ZERO_TO_ONE` define in
Chapter 01's `premake5.lua` makes GLM produce `[0, 1]` depth. That define, like
every `GLM_FORCE_*` switch, lives **once, in `premake5.lua`**, never as a
`#define` above an include: GLM's functions are inline templates whose bodies
depend on it, so two files that disagree compile two different versions of the
same function, and the linker silently keeps one.

> **Jump:** this is the first code that runs on the GPU, and it runs as many
> separate invocations at once: one per vertex, then one per fragment, none of
> which can see another. Keep in mind from here: a value reaches the fragment
> shader only through a vertex shader `out`, blended across the triangle, and
> anything else a shader needs must be handed to it — a push constant or a
> descriptor, Chapter 08.

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

Draw with `vkCmdDraw(cmd, 3, 1, 0, 0)`. One oversized triangle is measurably
faster than two triangles forming a quad, because the quad's diagonal makes
every 2x2 pixel block along it shade twice. (GPUs shade pixels in 2x2 blocks;
Chapter 15 section 5 says why.)

---

## 3. Shader modules

First, getting the words off disk — in `ExecutableFiles.cpp`, beside
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
    file.read(reinterpret_cast<char*>(words.data()), bytes);
    return words;
}
```

Then the module:

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
    vkCreateShaderModule(device, &moduleInfo, nullptr, &module);
    return module;
}
```

Two traps in four lines:

- **`codeSize` is in bytes, `pCode` is `uint32_t*`.** Read into a
  `std::vector<uint32_t>` and the size arithmetic stays honest. A
  `std::vector<char>` is in fact suitably aligned — it allocates through
  `operator new` — so the cast is legal; what it costs you is a `reinterpret_cast`
  at every use and a `size()` that means bytes in one line and words in the next.
  That is where the off-by-four comes from, not from alignment.
- **Shader modules are consumed at pipeline creation.** Destroy them
  immediately after `vkCreateGraphicsPipelines` returns. Keeping them alive is a
  common leak, and there is nothing to keep them alive for.

---

## 4. The graphics pipeline

Almost all fixed-function state is immutable and baked in here. That is the
trade: you pay a big up-front object, and you get no driver-side state
validation at draw time.

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

vkCreateGraphicsPipelines(m_device, m_pipelineCache, 1, &pipelineInfo, nullptr, &m_pipeline);
```

### Things worth knowing rather than copying

**`VkPipelineRenderingCreateInfo` replaces the render pass entirely.** The
pipeline needs to know attachment *formats* to compile the fragment output, not
a render pass object. This means **your pipeline survives swapchain
recreation** as long as the format is unchanged — and the format only changes
if the surface itself changed, which is rare. Rebuilding pipelines on resize
stops being a thing you do, which is one of dynamic rendering's real wins.

**Dynamic viewport and scissor are not optional in practice.** Without them,
every resize rebuilds every pipeline. With them, you call
`vkCmdSetViewport`/`vkCmdSetScissor` each frame and nothing else changes. Note
that `viewportCount` and `scissorCount` must still be 1 in the create info even
though the values are dynamic.

**The viewport Y flip, and why this tutorial does not use it.** Many engines
give the viewport a negative height, which turns Vulkan's Y-down into OpenGL's
Y-up. It is legal (core since 1.1), but it also reverses winding, so
`frontFace` must flip with it, and applying a flip in two places is the
classic cause of inside-out models. This tutorial keeps the viewport positive
and flips once, in the projection matrix (Chapter 10 section 2).

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

Even with nothing to bind, you need a layout:

```cpp
const VkPipelineLayoutCreateInfo layoutInfo{
    .sType                  = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
    .setLayoutCount         = 0,
    .pushConstantRangeCount = 0,
};
vkCreatePipelineLayout(m_device, &layoutInfo, nullptr, &m_pipelineLayout);
```

Chapter 08 fills this in with the push constant range that carries your ImGui
slider values.

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
vkCreatePipelineCache(m_device, &cacheInfo, nullptr, &m_pipelineCache);
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
vkCreatePipelineCache(m_device, &cacheInfo, nullptr, &m_pipelineCache);
```

And the two file functions, in `ExecutableFiles.cpp`:

```cpp
// The saved blob, or empty if there is none or it was written by a different
// device or driver - which vkCreatePipelineCache would not tell you.
std::vector<char> loadPipelineCache(const VkPhysicalDeviceProperties& device)
{
    std::ifstream file(executableDirectory() / "pipeline_cache.bin", std::ios::binary);
    std::vector<char> blob((std::istreambuf_iterator<char>(file)), std::istreambuf_iterator<char>());

    VkPipelineCacheHeaderVersionOne header{};
    if (blob.size() < sizeof(header)) { return {}; }
    std::memcpy(&header, blob.data(), sizeof(header));

    const bool matches = header.headerVersion == VK_PIPELINE_CACHE_HEADER_VERSION_ONE
                      && header.vendorID      == device.vendorID
                      && header.deviceID      == device.deviceID
                      && std::memcmp(header.pipelineCacheUUID, device.pipelineCacheUUID,
                                     VK_UUID_SIZE) == 0;
    return matches ? blob : std::vector<char>{};
}

// Called from shutdown, after vkDeviceWaitIdle and before vkDestroyPipelineCache.
void savePipelineCache(VkDevice device, VkPipelineCache cache)
{
    if (cache == VK_NULL_HANDLE) { return; }   // initialize failed before creating it

    size_t size = 0;
    vkGetPipelineCacheData(device, cache, &size, nullptr);
    std::vector<char> blob(size);
    vkGetPipelineCacheData(device, cache, &size, blob.data());

    std::ofstream file(executableDirectory() / "pipeline_cache.bin", std::ios::binary);
    file.write(blob.data(), static_cast<std::streamsize>(size));
}
```

**Why the header check.** The blob is specific to one GPU and driver, and
`vkCreatePipelineCache` will not tell you when it is stale: an incompatible
blob is silently ignored, and a truncated or corrupt one is undefined behavior
some drivers crash on. On a machine with two GPUs, switching with `--gpu`
(Chapter 05) makes the saved blob the other device's. So `loadPipelineCache`
reads the `VkPipelineCacheHeaderVersionOne` at the front of the blob itself and
starts cold on any mismatch. A bad cache is never a fatal error.

---

## 7. Drawing

**This is `recordFrame`**, inside Chapter 05's rendering scope:

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
section 6 moves the triangle into its own demo. The renderer grows by:

```cpp
// Added to VulkanRenderer's private members (Chapter 04's class map).
VkPipelineCache  m_pipelineCache  = VK_NULL_HANDLE;   // section 6
VkPipelineLayout m_pipelineLayout = VK_NULL_HANDLE;   // section 5
VkPipeline       m_pipeline       = VK_NULL_HANDLE;   // section 4
```

- **In `initialize`**, after the swapchain (the pipeline needs its format):
  the cache (section 6's code), then the layout, then the pipeline. Keep the
  last two in a private `createTrianglePipeline()`, so `initialize` stays a
  list of steps. Create both shader modules just before
  `vkCreateGraphicsPipelines` and destroy them right after it.
- **In `recordFrame`**, section 7's viewport, scissor, bind, and draw, inside
  Chapter 05's rendering scope.
- **In `shutdown`**, after `vkDeviceWaitIdle` and before the swapchain, in
  reverse: `vkDestroyPipeline`, `vkDestroyPipelineLayout`, then
  `savePipelineCache`, then `vkDestroyPipelineCache`.
  Null handles are valid no-ops, so a partial `initialize` is still safe.

Chapter 02's "no leaked objects" exit check keeps passing only if every chapter
adds its `shutdown` lines along with its `initialize` lines.

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
attachment. The two fields beyond what the triangle needs are there because
the next two pipelines need them: Chapter 08's composite pass has a
specialization constant, and Chapter 10's cubes test depth. Chapter 11 grows
the desc once more, with vertex input, culling, and extra dynamic state, when
meshes arrive.

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
still be using, so it needs a small deletion queue that holds objects for
`FRAMES_IN_FLIGHT` frames first. ROADMAP defers hot reload; the deletion queue
arrives with it.

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

- [ ] After regenerating (new shaders and new `ExecutableFiles` sources),
      building emits both `.spv` files under the executable's directory,
      mirroring their source folders.
- [ ] The triangle renders when launched from Visual Studio, from Explorer, and
      from a terminal — three different working directories, one correct path.
- [ ] The triangle renders and survives resize without pipeline recreation.
- [ ] Debug SPIR-V shows readable source in RenderDoc: capture a frame, select
      the draw, and open the vertex shader from Pipeline State. (Chapter 34
      sections 1-3 walk through RenderDoc, from taking the capture to Pipeline
      State; read them now if RenderDoc is new to you.)

Next: [07 — ImGui Debug Panels](07-ImGui.md)
