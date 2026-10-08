# 15 — Materials and Textures

**Goal:** a USD scene arrives with its materials — textured, mipmapped,
normal-mapped, metallic or rough where the file says so, with leaves cut out of
their quads — shaded by a physically based BRDF that is still lit by Chapter
11's one sun. The chapter has two parts. **Part 1, Textures** (sections 1-8),
gets every material's images onto the GPU and draws them under Chapter 11's
Lambert lighting. **Part 2, Surfaces** (sections 9-13), adds what makes a
material look like one: three shading models side by side, normal maps, and
cutouts.

**ROADMAP:** step 16.

**Module:** three, because a material crosses all three layers:

- `Source/PillowFort/Scene/`, `pf::scene` — `Material` grows into
  UsdPreviewSurface, `TextureImage` holds decoded pixels, and
  `generateTangents` fills the tangent the `Vertex` has carried since Chapter 11.
  Still Vulkan-free.
- `Source/PillowFort/UsdImport/UsdImport.cpp`, `pf::usd_import` — reading a
  material's shader network and decoding its images. Still the only file that
  includes TinyUSDZ.
- `Source/PillowFort/VulkanGraphics/`, `pf::vulkan_graphics` — `GpuTexture`
  (upload with a full mip chain), and `SceneRenderer`'s set 1: one descriptor
  set per material.

Shaders: `Shaders/Scene/Mesh.vert.glsl` and `Mesh.frag.glsl` are rewritten, and
two includes join `Shaders/Include/`.

**Math:** taught here — how many levels a mip chain has, and how the sampler
picks one from screen-space derivatives and a `log2` (section 5); radiance,
irradiance, and a BRDF, with Lambert's 1/π, Schlick's Fresnel, a normalized
highlight lobe, and GGX's distribution and shadowing terms (section 9);
solving two equations for a tangent, optional (section 10). Assumed: the dot
product as a cosine (Chapter 11 section 14), the cross product and Chapter 12
section 5's mirror test, and powers and logarithms.

**Prerequisites:**

- Chapter 02 sections 5-7 — the feature chain this chapter adds
  `samplerAnisotropy` (section 5) and `shaderDemoteToHelperInvocation`
  (section 11) to.
- Chapter 04 section 5 — the three questions every barrier answers, the rule
  that a barrier's second half reaches every later command on the queue, and
  `transitionImage`. This chapter writes barriers on single mip levels.
- Chapter 06 section 8 — `GraphicsPipelineDesc` and its
  `fragmentSpecialization` field; Chapter 08 section 4 — specialization
  constants themselves (the composite's `encodeSrgb`).
- Chapter 08 sections 3, 4, 6, 7, and 8 — images and samplers, the color
  boundary table (`_SRGB` for color, `UNORM` for data), descriptor sets and pool
  sizing, VMA, and `SharedShaderTypes.h`.
- Chapter 10 section 7 — `FrameData`, which is append-only, and the rule that
  host writes made before `vkQueueSubmit2` need no barrier.
- Chapter 11 — `Vertex` (its `tangent`), `Material`, `DrawData`,
  `SceneRenderer`'s pipelines and `ShadingMode`, the mesh shaders this chapter
  rewrites, and section 10's Lambert cosine as a dot product.
- Chapter 12 — `Scene`, `DrawItem`, `Submesh::materialIndex`, and
  `DEFAULT_MATERIAL`; section 5's mirror test, `dot(cross(x, y), z) < 0`.
- Chapters 13 and 14 — TinyUSDZ with its image loader compiled in, and
  `UsdImport.cpp`'s `ImportContext`, `importPrim`, and `importMesh`, which this
  chapter extends. Chapter 14 already flipped USD's texture coordinates into the
  engine's top-left convention, so nothing here flips them again.

---

## What you are actually writing

A material is the first thing in this tutorial that exists in all three layers
at once, so it is worth seeing the whole route before any of it:

```text
 USD file                      UsdImport.cpp (sections 2-4)           Scene (section 3)
 Material ──▶ UsdPreviewSurface ──▶ importMaterial ──▶ scene::Material ─┐   plain data:
              └─ UsdUVTexture ──▶ importTextureImage ──▶ scene::TextureImage   numbers, pixels,
                                                                        │   texture indices
 ───────────────────────────────────────────────────────────────────────┼──────────────────
 SceneRenderer (sections 5-7)                                           ▼
   AddTexture ──▶ GpuTexture (mip chain, section 5)                    UsdViewerDemo::Setup
   AddMaterial ──▶ MaterialParameters uniform buffer + set 1 ◀──────── uploads both, in
   RecordDraws ──▶ binds set 1 when the material changes                index order
 ───────────────────────────────────────────────────────────────────────────────────────────
 Mesh.frag.glsl: samples set 1 (section 8); a BRDF, normal maps, cutouts (sections 9-11)
```

The files, and what each section adds to them:

```text
Part 1 - Textures
Scene/Material.h            Material grows; TextureWrap, TextureInput, TextureImage   section 3
Scene/Scene.h/.cpp          AddTexture, GetTexture, TextureCount                      section 3
UsdImport/UsdImport.cpp     importMaterial and its helpers, resolveMaterials          section 4
VulkanInstance.cpp          samplerAnisotropy                                         section 5
VulkanGraphics/GpuTexture.h/.cpp     GpuTexture, uploadTexture, createMaterialSampler  section 5
Shaders/Include/SharedShaderTypes.h  TextureTransform, MaterialParameters              section 6
VulkanGraphics/SceneRenderer.h/.cpp  set 1, AddTexture, AddMaterial, RecordDraws       section 7
Shaders/Include/MaterialSet.glsl     set 1's declarations and helpers                  section 8
Shaders/Scene/Mesh.frag.glsl         set 1's textures under Chapter 11's Lambert       section 8
Demos/UsdViewer/UsdViewerDemo.cpp    textures before materials; the mip-level view     sections 7, 8

Part 2 - Surfaces
Shaders/Include/PreviewSurface.glsl  three BRDFs: Lambert, Blinn-Phong, GGX            section 9
Shaders/Include/SharedShaderTypes.h  FrameData::brdf, the switch between them          section 9
Demos/UsdViewer/UsdViewerDemo.h/.cpp the BRDF switch; the last debug view             sections 9, 11
Scene/Tangents.h/.cpp       generateTangents                                          section 10
Scene/MeshGenerators.cpp    one generateTangents call per generator                   section 10
UsdImport/UsdImport.cpp     generateTangents at the top of addMesh                    section 10
VulkanInstance.cpp          shaderDemoteToHelperInvocation, for discard               section 11
VulkanGraphics/GpuMesh.cpp           meshVertexAttributes() gains the tangent          section 11
Shaders/Scene/Mesh.vert.glsl, Mesh.frag.glsl   the tangent; normal maps and cutouts   section 11
Shaders/Include/MaterialSet.glsl     materialOpacity                                   section 11
VulkanGraphics/SceneRenderer.cpp     a cutout pipeline per shading mode                section 11
```

### What `SceneRenderer` gains

Chapter 11's class map, with this chapter's additions marked. Everything not
shown is unchanged. Two of them belong to Part 2 — `ShadingMode`'s fourth value
and the second dimension of `m_meshPipelines` (section 11) — and Part 1 leaves
them out; `GpuMaterial::cutout` is recorded from Part 1 on and used in
section 11:

```cpp
// Source/PillowFort/VulkanGraphics/SceneRenderer.h - Chapter 15's additions.
enum class ShadingMode : uint32_t
{
    Lit                  = 0,   // Chapter 11
    Normals              = 1,   // Chapter 11; from here on, the normal-mapped normal
    MipLevel             = 2,   // section 8: which mip level each pixel samples
    LitWithoutNormalMaps = 3,   // section 11: the comparison for the exit check
};
inline constexpr uint32_t SHADING_MODE_COUNT = 4;   // 3 in Part 1

// The seven textures a material binds, in set 1 binding order (binding = slot + 1).
enum MaterialTextureSlot : uint32_t
{
    BaseColorSlot, EmissiveSlot, NormalSlot, MetallicSlot, RoughnessSlot, OcclusionSlot, OpacitySlot,
    MATERIAL_TEXTURE_COUNT,
};

// One material on the GPU: its parameters and the set that points at them and its textures.
struct GpuMaterial
{
    AllocatedBuffer parameters;                  // one MaterialParameters, host-visible
    VkDescriptorSet set    = VK_NULL_HANDLE;     // from m_materialPools; freed with its pool
    bool            cutout = false;              // opacityThreshold > 0: drawn with the cutout pipeline
};

class SceneRenderer
{
public:
    // ...Chapters 10-11 unchanged...
    uint32_t AddTexture(const scene::TextureImage& image);    // section 7: uploads now; returns its index
    // AddMaterial keeps Chapter 11's declaration; section 7 makes it build set 1 as well.

private:
    InitializationResult CreateMaterialResources();   // section 7: set 1 layout, samplers, white texture
    void                 DestroyMaterialResources();
    VkDescriptorSet      AllocateMaterialSet();       // section 7: from the newest pool, or a new one

    // Section 11: Chapter 11's m_meshPipelines gains a dimension, [ShadingMode][cutout].
    std::array<std::array<VkPipeline, 2>, SHADING_MODE_COUNT> m_meshPipelines{};

    // Chapter 15
    VkDescriptorSetLayout          m_materialSetLayout = VK_NULL_HANDLE;
    std::vector<VkDescriptorPool>  m_materialPools;              // grows as materials are added
    std::array<VkSampler, 16>      m_materialSamplers{};         // [wrapS * 4 + wrapT]
    GpuTexture                     m_whiteTexture;               // every untextured input reads this
    std::vector<GpuTexture>        m_textures;                   // index == the Scene's texture index
    std::vector<GpuMaterial>       m_gpuMaterials;               // index == m_materials' index
};
```

`SceneRenderer.h` gains `#include "PillowFort/VulkanGraphics/GpuTexture.h"`
(section 5) for the two texture members; `SceneRenderer.cpp` gains
`"PillowFort/ErrorReporting/Log.h"`, `<format>`, and
`<vulkan/vk_enum_string_helper.h>` (`string_VkResult`, section 7).

`Initialize` calls `CreateMaterialResources()` **between**
`CreateFrameResources()` and `CreatePipelines()`: the mesh pipeline layout
needs set 1's layout, so it must exist first.

```cpp
// SceneRenderer::Initialize (Chapter 15): set 1's layout before the pipelines that use it.
    if (auto result = CreateFrameResources(); !result)    { return result; }
    if (auto result = CreateMaterialResources(); !result) { return result; }   // Chapter 15: set 1
    if (auto result = CreatePipelines(); !result)         { return result; }   // needs sets 0 and 1
```

`Shutdown` calls `DestroyMaterialResources()` right after `DestroyPipelines()`,
before `DestroyFrameResources()` — the reverse order:

```cpp
// SceneRenderer::Shutdown (Chapter 15), after Chapter 11's mesh loop and m_materials.clear():
    DestroyPipelines();
    DestroyMaterialResources();   // Chapter 15: set 1, the textures, the samplers

    DestroyFrameResources();
```

> **Jump:** until now a draw carried everything about its surface in its own
> push constant — Chapter 11's `DrawData::baseColor`. From here a surface is
> *bound state*: a descriptor set that stays bound across draws until the next
> material replaces it. Keep two consequences in mind. A material is now
> something you create once and refer to by index, like a mesh. And the order
> draws arrive in starts to matter for cost — every change of material is a
> rebind. Chapter 19 sorts by it; here, `RecordDraws` simply rebinds when the
> material changes.

---

# Part 1 — Textures (sections 1-8)

Part 1 follows a material from the file to the screen: what UsdPreviewSurface
is, how the importer reads its shader network and decodes its images, how a
texture reaches the GPU with a full mip chain, and how one descriptor set per
material hands all of it to the fragment shader. Its shader is still Chapter
11's Lambert, with the color now read through the material. At the end you
load the test scene and check three things, by eye and by number: mipmaps at
work on a receding floor, a row of grey bands whose colors come out
byte-exact, and a missing texture reported and replaced.

## 1. The material model: UsdPreviewSurface

USD does not have one material model; it has a way to *describe* any shading
network, and a handful of standard nodes every renderer agrees to understand.
`UsdPreviewSurface` is the standard surface: deliberately small, physically
based, and the one every exporter writes — Blender's Principled BSDF becomes
one on export, as does Maya's standard surface. Implementing it is what makes
"a USD scene" render the same here as in the viewer that wrote it.

The physical meaning of `metallic`, `roughness`, and `ior` is section 9's
subject; for now, read them as knobs. UsdPreviewSurface's inputs, and what
this chapter does with each:

| Input | Default | Here |
| --- | --- | --- |
| `diffuseColor` | (0.18, 0.18, 0.18) | **Implemented** — `Material::baseColor`, Chapter 11's name for the same thing |
| `emissiveColor` | (0, 0, 0) | **Implemented** — added after lighting; may exceed 1 (Blender writes color × strength) |
| `metallic` | 0 | **Implemented** — the metallic workflow (section 9) |
| `roughness` | 0.5 | **Implemented** — squared before use, as the spec suggests (section 9) |
| `normal` | (0, 0, 1) | **Implemented** — tangent-space normal map (sections 10 and 11) |
| `occlusion` | 1 | **Implemented** — darkens ambient light only (section 9) |
| `opacity` | 1 | **Implemented for cutouts** — with `opacityThreshold` (section 11) |
| `opacityThreshold` | 0 | **Implemented** — above 0, pixels with `opacity` below it are discarded |
| `ior` | 1.5 | **Implemented** — sets a dielectric's head-on reflectance, 4% at 1.5 (section 9) |
| `useSpecularWorkflow`, `specularColor` | 0 | Ignored, with a warning. One workflow is enough to learn from, and exporters write metallic |
| `clearcoat`, `clearcoatRoughness` | 0 | Ignored, with a warning when nonzero. A second, glossier highlight over the first; easy to add once the first works |
| `displacement` | 0 | Ignored, with a warning. Moving vertices needs a finer mesh, made on the GPU (tessellation) or ahead of time |
| `opacityMode` | `"opacity"` | Ignored: without real transparency (section 12) there is nothing for it to choose between |

`UsdTransform2d`, which rotates and scales texture coordinates, is not read
either; a file that uses it renders with untransformed coordinates. Everything
ignored is *reported*: a material that renders differently from its source
without a word is the kind of bug that costs an afternoon.

---

## 2. How USD wires a texture to a material

A UsdPreviewSurface input is either a constant or a **connection** to another
node's output. Textures arrive as connections. Here is one material from this
chapter's test scene, whole:

```usda
def Material "Checker"
{
    token outputs:surface.connect = </MaterialTest/Materials/Checker/Surface.outputs:surface>

    def Shader "Surface"
    {
        uniform token info:id = "UsdPreviewSurface"
        color3f inputs:diffuseColor.connect = </MaterialTest/Materials/Checker/Albedo.outputs:rgb>
        float inputs:roughness = 0.9
        token outputs:surface
    }

    def Shader "Albedo"
    {
        uniform token info:id = "UsdUVTexture"
        asset inputs:file = @Textures/Checker.png@
        token inputs:sourceColorSpace = "sRGB"
        token inputs:wrapS = "repeat"
        token inputs:wrapT = "repeat"
        float2 inputs:st.connect = </MaterialTest/Materials/Checker/TexCoord.outputs:result>
        float3 outputs:rgb
    }

    def Shader "TexCoord"
    {
        uniform token info:id = "UsdPrimvarReader_float2"
        string inputs:varname = "st"
        float2 outputs:result
    }
}
```

Read it from the bottom up. `TexCoord` reads the mesh's `st` primvar — the
texture coordinates Chapter 14 already imported into `Vertex::uv`. `Albedo`
samples `Checker.png` at those coordinates. `Surface` takes its
`diffuseColor` from `Albedo`'s `rgb` output, and its roughness is a plain
constant. The `Material` prim itself only points at the surface.

What `UsdUVTexture` adds on top of "sample this file", one input at a time:

- **`file`** — a path relative to the USD file, or, in a `.usdz`, an entry in
  its archive. This chapter's importer reads only the first (section 4).
- **`wrapS`, `wrapT`** — `repeat`, `mirror`, `clamp`, or `black` outside
  `[0, 1]`. The default, `useMetadata`, means "whatever the image file says,
  else black". PNG and JPEG say nothing, so **an unauthored wrap mode is
  black**: a texture tiled across a floor that shows only its first tile, and
  black beyond, came from a file that left these unset. Blender always writes
  them.
- **`scale`, `bias`** — `output = texel * scale + bias`, per channel, applied
  after sampling. This is how an 8-bit normal map's `[0, 1]` becomes `[-1, 1]`
  (scale 2, bias −1), how glossiness becomes roughness (scale −1, bias 1), and
  how a DirectX-convention normal map is fixed in the file rather than in code
  (negate the green channel's scale and bias). Normal maps are section 10's.
- **`sourceColorSpace`** — `sRGB`, `raw`, or `auto`. Section 4 turns this into
  `_SRGB` or `UNORM`.
- **`fallback`** — the value the output takes when the file cannot be read.
  The importer uses it, and says why.
- **Outputs** — `r`, `g`, `b`, `a`, or `rgb`. Which one the material connected
  matters: packed textures put occlusion, roughness, and metallic in one
  image's red, green, and blue, and three inputs read three outputs of the
  same node.

One mapping rule makes the shader simple: **when an input is connected, the
texture's value replaces the constant.** UsdPreviewSurface does not multiply
them, as glTF does. Section 6 turns both cases into one multiply anyway, so the
shader never asks which case it is in.

---
## 3. Materials as plain data

`scene::Material` grows from Chapter 11's name and color into the table in
section 1. It stays plain data — numbers, and **indices** into the scene's
texture list — so the inspector, the importer, and the GPU side all read the
same struct and none of them depends on another.

Each textured input carries everything `UsdUVTexture` said about it, in a small
struct. Its defaults describe "no texture": an `image` of `NO_TEXTURE`, and a
remap that changes nothing.

```cpp
// Source/PillowFort/Scene/Material.h - Chapter 11's struct, grown. Includes <glm/glm.hpp>,
// <cstdint>, <string>, and <vector>.
#pragma once

#include <glm/glm.hpp>

#include <cstdint>
#include <string>
#include <vector>

namespace pf::scene {

// Index 0 is always there: a scene's constructor makes it (Chapter 12), and a
// mesh nobody assigned a material to uses it.
inline constexpr uint32_t DEFAULT_MATERIAL = 0;
inline constexpr uint32_t NO_TEXTURE       = UINT32_MAX;   // a TextureInput with no image (Chapter 15)

// UsdUVTexture's wrapS / wrapT. The order is used: SceneRenderer indexes its samplers with it.
enum class TextureWrap : uint32_t { Repeat = 0, Mirror = 1, Clamp = 2, Black = 3 };

// A decoded image, ready to upload: 8-bit RGBA, rows top to bottom, tightly packed.
struct TextureImage
{
    std::string          name;            // the asset path it came from - for log messages
    uint32_t             width  = 0;
    uint32_t             height = 0;
    bool                 srgb   = false;  // sRGB-encoded color: uploaded _SRGB, decoded when sampled
    std::vector<uint8_t> pixels;          // width * height * 4 bytes
};

// One material input driven by a UsdUVTexture.
struct TextureInput
{
    uint32_t    image   = NO_TEXTURE;           // index into the Scene's textures
    TextureWrap wrapS   = TextureWrap::Repeat;
    TextureWrap wrapT   = TextureWrap::Repeat;
    glm::vec4   scale   { 1.0f };               // value = texel * scale + bias
    glm::vec4   bias    { 0.0f };
    glm::vec4   channel { 1.0f, 0.0f, 0.0f, 0.0f };   // scalar inputs: the connected output as a mask
};

// UsdPreviewSurface, metallic workflow. A connected input's texture REPLACES its constant.
struct Material
{
    std::string name;
    glm::vec4   baseColor{ 0.8f, 0.8f, 0.8f, 1.0f };   // diffuseColor; LINEAR rgb (Chapter 11)
    glm::vec3   emissiveColor{ 0.0f };                  // linear rgb; may exceed 1
    float       metallic         = 0.0f;
    float       roughness        = 0.5f;
    float       occlusion        = 1.0f;
    float       opacity          = 1.0f;
    float       opacityThreshold = 0.0f;                // > 0: a cutout
    float       ior              = 1.5f;

    TextureInput baseColorTexture;
    TextureInput emissiveTexture;
    TextureInput normalTexture;                         // no constant: untextured means flat
    TextureInput metallicTexture;
    TextureInput roughnessTexture;
    TextureInput occlusionTexture;
    TextureInput opacityTexture;
};

} // namespace pf::scene
```

`baseColor`'s default stays Chapter 11's 0.8 grey, not USD's 0.18: procedural
scenes keep looking as they did, and the importer writes the file's value — or
USD's 0.18 fallback — whenever it reads a material.

Images live in the scene beside meshes and materials, and are uploaded the same
way: in index order, so a texture index means the same thing on both sides.
`Scene` grows three members, written like Chapter 12's `AddMaterial` /
`MaterialCount` / `GetMaterial`, and the vector behind them:

```cpp
// Source/PillowFort/Scene/Scene.h - added to Scene's public section, after the materials
// (Chapter 15).
uint32_t            AddTexture(TextureImage image);   // returns its index
std::size_t         TextureCount() const { return m_textures.size(); }
const TextureImage& GetTexture(uint32_t texture) const;
```

```cpp
// Scene.h, private, after m_materials (Chapter 15).
std::vector<TextureImage> m_textures;   // decoded, CPU-side; the renderer keeps the GPU copies
```

```cpp
// Scene.cpp, inside namespace pf::scene (Chapter 15).
uint32_t Scene::AddTexture(TextureImage image)
{
    m_textures.push_back(std::move(image));   // a few megabytes of pixels: moved, not copied
    return static_cast<uint32_t>(m_textures.size() - 1);
}

const TextureImage& Scene::GetTexture(uint32_t texture) const { return m_textures.at(texture); }
```

**Why decoded pixels and not file paths?** Because the decoder lives in
TinyUSDZ, and TinyUSDZ may only be included by `UsdImport.cpp` (Chapter 13). A
path would force the GPU side to decode, which means another image library, or
a TinyUSDZ include where none is allowed. A `.usdz` makes it worse: its
textures are not files at all, but entries inside a zip, which only the
importer's side of the engine could reach.

---

## 4. Reading a shader network in the importer

**This is `importMaterial` and its helpers** — file-scope functions in
`UsdImport.cpp`, added in this section's order just above `addMesh` (and so
above `importMesh` and `importShape`, which call them). Chapter 14 left two
hooks: `ImportContext`, which already carries the stage and the USD
file's folder and now gains two caches, and `importMesh`'s list of submesh
sources, which the last function in this section reads.

```cpp
// UsdImport.cpp - Chapter 14's ImportContext, with Chapter 15's two caches appended.
struct ImportContext
{
    pf::scene::Scene&          scene;
    const tinyusdz::Stage&     stage;                 // chapter 15 resolves material bindings through it
    std::filesystem::path      directory;             // the file's folder: chapter 15's texture paths
    double                     metersPerUnit = 1.0;   // the stage's, for camera distances
    std::map<std::string, int> skipped;               // prim type -> how many were skipped
    // Chapter 15:
    std::map<std::string, uint32_t>                  materials = {};   // material prim path -> scene material
    std::map<std::pair<std::string, bool>, uint32_t> textures  = {};   // (asset path, srgb) -> scene texture
};
```

`ImportUsdFile` names the two new members where Chapter 14 builds the context,
because g++ warns about a member left out of a designated initializer:

```cpp
    ImportContext context{
        .scene         = scene,
        .stage         = stage,
        .directory     = file.parent_path(),
        .metersPerUnit = metersPerUnit,
        .skipped       = {},
        .materials     = {},   // Chapter 15
        .textures      = {},   // Chapter 15
    };
```

Both are caches, and both are needed for the same reason: a file that binds one
material to two hundred meshes must produce one material and one texture, not
two hundred. The texture key includes the color space because one image can be
read both ways — a file marked `auto` is sRGB for a color input and raw for any
other (below) — and the two uses become two GPU images (section 5).

`UsdImport.cpp` gains `#include <image-loader.hh>` and
`#include <tydra/shader-network.hh>` beside Chapter 14's TinyUSDZ includes,
inside the same `#pragma warning` pair, and `<fstream>`, `<iterator>`, and
`<utility>`.

### Following a connection

A connection is a path to a *property*: `</Mat/Albedo.outputs:rgb>` names the
`outputs:rgb` property of the prim `/Mat/Albedo`. The prim part finds the node;
the property part says which output. TinyUSDZ stores every shader as a
`Shader` prim whose `value` holds the concrete node, so finding "the
`UsdUVTexture` this connection points at" is three steps, each of which can
fail on a file you did not write:

```cpp
// File scope, above the namespace block. The shader node a connection points at -
// "/Mat/Albedo.outputs:rgb" names the prim "/Mat/Albedo" - if that node is a T, else nullptr.
template <typename T>
static const T* connectedNode(const ImportContext& context, const tinyusdz::Path& connection)
{
    const auto prim = context.stage.GetPrimAtPath(tinyusdz::Path(connection.prim_part(), ""));
    if (!prim) { return nullptr; }
    const tinyusdz::Shader* shader = prim.value()->as<tinyusdz::Shader>();
    return shader != nullptr ? shader->value.as<T>() : nullptr;
}
```

`context.stage` is the `tinyusdz::Stage` Chapter 14's `ImportContext` holds.
The template returns `nullptr` for a MaterialX node, a `UsdTransform2d`
between the texture and the surface, or a path to nothing — each a file this
importer does not understand, and each reported by the caller.

### Wrap modes

```cpp
// File scope, above the namespace block. UsdUVTexture's wrap tokens. "useMetadata" means
// "whatever the image says, else black"; stb_image reports no wrap metadata, so it is black.
static pf::scene::TextureWrap toTextureWrap(tinyusdz::UsdUVTexture::Wrap wrap)
{
    using Wrap = tinyusdz::UsdUVTexture::Wrap;
    switch (wrap)
    {
    case Wrap::Repeat:      return pf::scene::TextureWrap::Repeat;
    case Wrap::Mirror:      return pf::scene::TextureWrap::Mirror;
    case Wrap::Clamp:       return pf::scene::TextureWrap::Clamp;
    case Wrap::Black:
    case Wrap::UseMetadata: return pf::scene::TextureWrap::Black;
    }
    return pf::scene::TextureWrap::Black;
}
```

### Decoding, and the color space decision

**Which decoder.** TinyUSDZ compiles `stb_image` into its own library
(Chapter 13), and exposes it as `tinyusdz::image::LoadImageFromMemory`. Using
it adds no dependency — ROADMAP's Guardrail 5 asks what a dependency removes,
and a second copy of `stb_image` would remove nothing. It is also why **nothing
in PillowFort may define `STB_IMAGE_IMPLEMENTATION`**: the symbols already exist
inside TinyUSDZ's library, and a second definition is a duplicate-symbol link
error. It handles PNG, JPEG, BMP, TGA, and Radiance HDR.

Two facts about it shape the code below. It **always returns four channels** —
a grey PNG comes back as (g, g, g, 255), which is exactly UsdUVTexture's rule
for one-channel files, so nothing needs expanding. And it returns **8 or 16
bits per channel**, as the file has them.

Read the file into memory first, rather than calling a load-from-file
function, so the decoder never needs a path. (TinyUSDZ's header also declares
`GetImageInfoFromFile`, but v0.9.4 never defines it — call it and the link
fails. The from-memory version works.)

**Textures come from beside the USD file only.** A `.usdz` packs its textures
inside its zip archive, and nothing in this importer opens the archive, so a
`.usdz` imports with every texture "not found" and every textured input at its
fallback. Reading them is an extension — a second branch in `readAssetBytes`
that finds the entry in the archive and returns its bytes. Until you write it,
export `.usdc` or `.usda` with *Textures* ticked, which puts the images in a
folder beside the file (section 13).

```cpp
// File scope, above the namespace block. An asset's bytes, read from beside the USD file.
// Empty when there is no such file - including a texture packed inside a .usdz, whose
// archive nothing here opens (section 4).
static std::vector<uint8_t> readAssetBytes(const ImportContext& context, const std::string& assetPath)
{
    // USD stores asset paths as UTF-8, but on Windows a path made from a std::string reads
    // it in the ANSI code page and misses any non-ASCII file name, so build it from char8_t
    // (Chapter 13 section 13's toUtf8, the other way round).
    const std::u8string utf8(assetPath.begin(), assetPath.end());
    std::ifstream file(context.directory / utf8, std::ios::binary);
    return std::vector<uint8_t>(std::istreambuf_iterator<char>(file), std::istreambuf_iterator<char>());
}
```

**The color space** is the decision Chapter 08 section 4 was written for:
color is stored sRGB-encoded and must be decoded when sampled (`_SRGB`), data
must reach the shader untouched (`UNORM`). `sRGB` and `raw` in the file decide
it directly. `auto` is UsdPreviewSurface's rule: *8-bit with three or four
channels is sRGB, anything else is raw.*

Applied literally, that rule decodes every 8-bit RGB normal map as if it were a
photograph, which bends every normal it contains. In numbers: a flat texel,
(128, 128, 255), should decode to (0.502, 0.502, 1.0) and remap to the normal
(0, 0, 1). Decoded as sRGB, 128 becomes 0.216, the remap gives an x and y of
−0.57, and the "flat" normal leans 39°: the whole surface is lit as if tilted.
The spec itself warns about this and tells authors to write `raw` on data
textures; Blender always does. A hand-written or older file may not, so this
importer applies `auto`'s rule only to the inputs that **are** colors —
`diffuseColor` and `emissiveColor` — and treats `auto` on any other input as
`raw`. That is a deliberate departure from the letter of the spec, in the
direction of the spec's own advice.

The rule needs the file's *own* channel count, which decoding — forced to four
— has already lost; `GetImageInfoFromMemory` reports it.

**16-bit images** come back with two bytes per channel. Vulkan has no 16-bit
`_SRGB` format, so a 16-bit color texture has to become 8-bit to be decoded by
the sampler anyway. For a 16-bit *data* texture — a high-precision normal map —
`R16G16B16A16_UNORM` would keep the precision, at the price of a second upload
path and a format-support check. This chapter reduces both to 8 bits, rounding,
and says so in the log; the 16-bit path is the place to start if a mirror-smooth
surface ever shows banding in its highlight.

```cpp
// File scope, above the namespace block. Decodes one texture into the scene, once per
// (asset, color space). colorInput: the material input is a color (section 4's `auto` rule).
static uint32_t importTextureImage(ImportContext& context, const std::string& assetPath, bool colorInput,
                                   tinyusdz::UsdUVTexture::SourceColorSpace space)
{
    using Space = tinyusdz::UsdUVTexture::SourceColorSpace;
    const std::vector<uint8_t> bytes = readAssetBytes(context, assetPath);
    if (bytes.empty())
    {
        Log::warning(std::format("Texture {} not found.", assetPath).c_str());
        return pf::scene::NO_TEXTURE;
    }

    // "auto" needs the file's own channel count, which decoding (forced to RGBA) loses.
    auto info    = tinyusdz::image::GetImageInfoFromMemory(bytes.data(), bytes.size(), assetPath);
    auto decoded = tinyusdz::image::LoadImageFromMemory(bytes.data(), bytes.size(), assetPath);
    if (!info || !decoded)
    {
        Log::warning(std::format("Texture {} could not be decoded: {}", assetPath,
                                 decoded ? info.error() : decoded.error()).c_str());
        return pf::scene::NO_TEXTURE;
    }
    const tinyusdz::Image& image = decoded.value().image;
    if (image.format != tinyusdz::Image::PixelFormat::UInt || (image.bpp != 8 && image.bpp != 16))
    {
        Log::warning(std::format("Texture {} is not an 8- or 16-bit image; skipped.", assetPath).c_str());
        return pf::scene::NO_TEXTURE;
    }

    const bool srgb = space == Space::SRGB ||
                      (space == Space::Auto && colorInput && image.bpp == 8 &&
                       (info.value().channels == 3 || info.value().channels == 4));

    const auto key = std::make_pair(assetPath, srgb);
    if (auto found = context.textures.find(key); found != context.textures.end()) { return found->second; }

    pf::scene::TextureImage texture{
        .name   = assetPath,
        .width  = static_cast<uint32_t>(image.width),
        .height = static_cast<uint32_t>(image.height),
        .srgb   = srgb,
    };
    const size_t texels = size_t(image.width) * size_t(image.height) * 4;
    texture.pixels.resize(texels);
    if (image.bpp == 8)
    {
        std::copy(image.data.begin(), image.data.begin() + texels, texture.pixels.begin());
    }
    else
    {
        // 16 bits per channel, native byte order: keep the top 8, rounded.
        Log::warning(std::format("Texture {} is 16-bit; reduced to 8 bits per channel.", assetPath).c_str());
        const uint16_t* wide = reinterpret_cast<const uint16_t*>(image.data.data());
        for (size_t i = 0; i < texels; ++i)
        {
            texture.pixels[i] = static_cast<uint8_t>((wide[i] + 128u) / 257u);
        }
    }
    const uint32_t index = context.scene.AddTexture(std::move(texture));
    context.textures.emplace(key, index);
    return index;
}
```

Radiance `.hdr` files decode as floating point and are skipped with the
message above: an HDR image in a material is almost always an environment map,
which is the DomeLight's business (Chapter 16), not a surface's.

### One textured input

Every input — color, scalar, or normal — goes through the same function. It
follows the connection, fills a `TextureInput` from the `UsdUVTexture` node,
and decodes its file. It fills a *local* and assigns it only on success: a node
whose file is missing must leave the input at "no texture", not half-filled with
a scale and bias that would then remap the white default texture into
something strange.

On failure the material still needs a value, and UsdUVTexture defines one —
its `fallback` input. The function hands it back, reduced to what the input
needs: all four channels for a color, the connected channel for a scalar.

```cpp
// File scope, above the namespace block. If `input` is connected to a UsdUVTexture, fills
// `texture` from it and returns true. If the connection exists but the texture cannot be
// used, returns false with `fallbackOut` set to the node's fallback value - USD's rule for a
// texture that cannot be read - which the caller uses as the input's constant.
template <typename T>
static bool importTextureInput(ImportContext& context, const tinyusdz::TypedAttributeWithFallback<T>& input,
                               bool colorInput, pf::scene::TextureInput& texture, glm::vec4& fallbackOut)
{
    if (!input.is_connection()) { return false; }
    const tinyusdz::Path& connection = input.get_connections()[0];
    pf::scene::TextureInput result;

    const tinyusdz::UsdUVTexture* node = connectedNode<tinyusdz::UsdUVTexture>(context, connection);
    if (node == nullptr)
    {
        Log::warning(std::format("{} is connected to something other than a UsdUVTexture; using its constant.",
                                 connection.full_path_name()).c_str());
        return false;
    }

    // Which output the material reads: outputs:r, g, b, a, or rgb.
    const std::string& output = connection.prop_part();
    result.channel = output == "outputs:g" ? glm::vec4(0, 1, 0, 0)
                   : output == "outputs:b" ? glm::vec4(0, 0, 1, 0)
                   : output == "outputs:a" ? glm::vec4(0, 0, 0, 1)
                   :                         glm::vec4(1, 0, 0, 0);   // r, or rgb (colors ignore it)

    tinyusdz::UsdUVTexture::Wrap wrapS = tinyusdz::UsdUVTexture::Wrap::UseMetadata;
    tinyusdz::UsdUVTexture::Wrap wrapT = tinyusdz::UsdUVTexture::Wrap::UseMetadata;
    node->wrapS.get_value().get_default(&wrapS);
    node->wrapT.get_value().get_default(&wrapT);
    result.wrapS = toTextureWrap(wrapS);
    result.wrapT = toTextureWrap(wrapT);

    const tinyusdz::value::float4 scale = node->scale.get_value();
    const tinyusdz::value::float4 bias  = node->bias.get_value();
    result.scale = glm::vec4(scale[0], scale[1], scale[2], scale[3]);
    result.bias  = glm::vec4(bias[0], bias[1], bias[2], bias[3]);

    tinyusdz::UsdUVTexture::SourceColorSpace space = tinyusdz::UsdUVTexture::SourceColorSpace::Auto;
    node->sourceColorSpace.get_value().get_default(&space);

    tinyusdz::value::AssetPath asset;
    const auto file = node->file.get_value();
    if (file && file.value().get_default(&asset) && !asset.GetAssetPath().empty())
    {
        result.image = importTextureImage(context, asset.GetAssetPath(), colorInput, space);
    }
    if (result.image == pf::scene::NO_TEXTURE)
    {
        // The value the input takes instead: the fallback's rgb for a color, its connected
        // channel for a scalar.
        const tinyusdz::value::color4f fallback = node->fallback.get_value();
        const glm::vec4 rgba(fallback.r, fallback.g, fallback.b, fallback.a);
        fallbackOut = colorInput ? rgba : glm::vec4(glm::dot(rgba, result.channel));
        return false;
    }
    texture = result;
    return true;
}
```

The `get_value().get_default(...)` pattern reads an attribute's value at the
default time, or its schema fallback when the file did not author it — the same
way Chapter 14 reads every attribute. A time-sampled material input (rare)
keeps its fallback.

### The material

**This is `importMaterial`.** It finds the surface the `Material` prim points
at, reads every input of section 1's table, and adds one `scene::Material`.
Two outcomes are reported rather than drawn wrong: a material whose surface is
not a UsdPreviewSurface (MaterialX, a renderer-specific shader) becomes the
default material, and the features section 1 ignores are named once per
material.

```cpp
// File scope, above the namespace block. One UsdPreviewSurface material, read once per prim.
// Returns its index in the scene's materials.
static uint32_t importMaterial(ImportContext& context, const tinyusdz::Prim& materialPrim)
{
    const std::string path = materialPrim.absolute_path().full_path_name();
    if (auto found = context.materials.find(path); found != context.materials.end()) { return found->second; }

    const tinyusdz::Material* usdMaterial = materialPrim.as<tinyusdz::Material>();
    const tinyusdz::UsdPreviewSurface* surface = nullptr;
    if (usdMaterial != nullptr && !usdMaterial->surface.get_connections().empty())
    {
        surface = connectedNode<tinyusdz::UsdPreviewSurface>(context, usdMaterial->surface.get_connections()[0]);
    }
    if (surface == nullptr)
    {
        Log::warning(std::format("Material {} has no UsdPreviewSurface; using the default material.", path).c_str());
        context.materials.emplace(path, pf::scene::DEFAULT_MATERIAL);
        return pf::scene::DEFAULT_MATERIAL;
    }

    pf::scene::Material material{ .name = materialPrim.element_name() };
    glm::vec4 fallback{ 0.0f };

    tinyusdz::value::color3f color{};
    surface->diffuseColor.get_value().get_default(&color);
    material.baseColor = glm::vec4(color.r, color.g, color.b, 1.0f);
    if (!importTextureInput(context, surface->diffuseColor, true, material.baseColorTexture, fallback) &&
        surface->diffuseColor.is_connection())
    {
        material.baseColor = glm::vec4(glm::vec3(fallback), 1.0f);
    }

    surface->emissiveColor.get_value().get_default(&color);
    material.emissiveColor = glm::vec3(color.r, color.g, color.b);
    if (!importTextureInput(context, surface->emissiveColor, true, material.emissiveTexture, fallback) &&
        surface->emissiveColor.is_connection())
    {
        material.emissiveColor = glm::vec3(fallback);
    }

    // The four scalar inputs share one shape: constant, or texture, or the texture's fallback.
    auto scalar = [&](const auto& input, float& value, pf::scene::TextureInput& texture) {
        input.get_value().get_default(&value);
        if (!importTextureInput(context, input, false, texture, fallback) && input.is_connection())
        {
            value = fallback.x;
        }
    };
    scalar(surface->metallic,  material.metallic,  material.metallicTexture);
    scalar(surface->roughness, material.roughness, material.roughnessTexture);
    scalar(surface->occlusion, material.occlusion, material.occlusionTexture);
    scalar(surface->opacity,   material.opacity,   material.opacityTexture);
    surface->opacityThreshold.get_value().get_default(&material.opacityThreshold);
    surface->ior.get_value().get_default(&material.ior);

    importTextureInput(context, surface->normal, false, material.normalTexture, fallback);

    // What this renderer does not draw: say so once per material, rather than drawing it wrong silently.
    int   specularWorkflow = 0;
    float clearcoat        = 0.0f;
    float displacement     = 0.0f;
    surface->useSpecularWorkflow.get_value().get_default(&specularWorkflow);
    surface->clearcoat.get_value().get_default(&clearcoat);
    surface->displacement.get_value().get_default(&displacement);
    if (specularWorkflow != 0 || clearcoat > 0.0f || displacement != 0.0f || surface->displacement.is_connection())
    {
        Log::warning(std::format("Material {}: specular workflow, clearcoat, and displacement are not drawn.",
                                 path).c_str());
    }
    const bool translucent = material.opacity < 1.0f || material.opacityTexture.image != pf::scene::NO_TEXTURE;
    if (material.opacityThreshold <= 0.0f && translucent)
    {
        Log::warning(std::format("Material {} is transparent (opacity without opacityThreshold); drawn opaque.",
                                 path).c_str());
    }

    const uint32_t index = context.scene.AddMaterial(material);
    context.materials.emplace(path, index);
    return index;
}
```

Blender writes `clearcoat = 0` on every material it exports, which is why the
warning tests the *value* and not whether the input was authored.

### Which material a mesh uses

USD binds a material to geometry with a `material:binding` relationship — on
the mesh, on any ancestor (a binding on an `Xform` applies to everything
beneath it), or on a `GeomSubset` that covers some of the mesh's faces.
Blender writes one on the mesh **and** one on each subset; the subset wins for
its faces. Resolving "which material applies here" walks up the hierarchy and
checks collection bindings too, and TinyUSDZ's Tydra layer implements exactly
that walk: `tinyusdz::tydra::GetBoundMaterial`.

Chapter 14's `importMesh` already split each mesh into submeshes — one per
`materialBind` subset, in authored order, then one for the faces no subset
covers — and kept a parallel list, `sources`, of the `GeomSubset` each came
from (`nullptr` for the remainder, or for a mesh without subsets). That list is
the hook. **This is `resolveMaterials`**, and `importMesh` calls it right after
the submeshes are built:

```cpp
// File scope, above the namespace block. Sets each submesh's material from the binding on
// its GeomSubset, else from the binding on the mesh (or the nearest bound ancestor).
static void resolveMaterials(ImportContext& context, const tinyusdz::Prim& meshPrim,
                             const std::vector<const tinyusdz::GeomSubset*>& sources,
                             std::vector<pf::scene::Submesh>& submeshes)
{
    // Returns DEFAULT_MATERIAL when nothing is bound.
    auto boundMaterial = [&](const tinyusdz::Path& primPath) {
        tinyusdz::Path materialPath;
        const tinyusdz::Material* material = nullptr;
        std::string error;
        if (!tinyusdz::tydra::GetBoundMaterial(context.stage, primPath, "", &materialPath, &material, &error) ||
            material == nullptr)
        {
            return pf::scene::DEFAULT_MATERIAL;
        }
        const auto prim = context.stage.GetPrimAtPath(materialPath);
        return prim ? importMaterial(context, *prim.value()) : pf::scene::DEFAULT_MATERIAL;
    };

    const uint32_t meshMaterial = boundMaterial(meshPrim.absolute_path());
    for (size_t i = 0; i < submeshes.size(); ++i)
    {
        const tinyusdz::GeomSubset* subset = sources[i];
        submeshes[i].materialIndex = meshMaterial;
        if (subset != nullptr)
        {
            // A subset's own binding wins for its faces; an unbound subset keeps the mesh's.
            const tinyusdz::Path subsetPath = meshPrim.absolute_path().AppendElement(subset->name);
            const uint32_t subsetMaterial = boundMaterial(subsetPath);
            if (subsetMaterial != pf::scene::DEFAULT_MATERIAL) { submeshes[i].materialIndex = subsetMaterial; }
        }
    }
}
```

```cpp
// In importMesh, after the loop that pushes one Submesh per source, before the log line that
// lists them (Chapter 15). Every submesh exists by then, each with its source at the same index.
resolveMaterials(context, prim, sources, data.submeshes);
```

The empty string is the binding *purpose*: USD lets a file bind a `preview`
material for viewers and a `full` one for final renders, and `""` asks for the
all-purpose binding, falling back as the spec says. Chapter 14's `importShape`
(spheres and cubes) makes one submesh, so it calls the same function with a
`sources` list of one `nullptr`:

```cpp
// In importShape, before its addMesh call (Chapter 15). `shape` is its MeshData parameter.
resolveMaterials(context, prim, { nullptr }, shape.submeshes);
```

**Try it now.** Nothing on the GPU has changed, and for a first look nothing
needs to: Chapter 14's viewer already hands every material to `AddMaterial`,
and Chapter 11's `RecordDraws` puts each draw's `baseColor` in its push
constant. So build, and open `BlenderScene.usdc` (Chapter 14 section 15) in the
viewer: the crate is red with a blue top, the ball yellow, the cone green —
Blender's colors, imported by this section and drawn by Chapter 11's shader.
If you save `MaterialTest.usda` from Appendix A and run Appendix B's script now
(section 8 says where), it shows the importer's decisions too: the log names
`Textures/DoesNotExist.png`, and `MissingPanel` is magenta, its texture node's
fallback; the floor and `LeafPanel` are USD's 0.18 grey, the constant under
their textures, which nothing samples yet; and `GreyBandsPanel` is black, its
diffuse color, because its picture is an emission texture.

---

## 5. Textures on the GPU

**This is `GpuTexture.h` and `GpuTexture.cpp`** — the upload with its mip chain,
and the samplers — plus the device feature the samplers need. First, what a mip
chain is and how the GPU uses one, because everything else here builds on it.

### The mip chain

A texture sampled at a distance, without mipmaps, is a texture sampled
sparsely: every screen pixel picks one texel out of the dozens it covers, and
which one changes as the camera moves. The result shimmers — the checkerboard
floor of section 8's test scene crawls with **moiré**, false wavy patterns that
appear when a fine pattern is sampled too coarsely. **Mipmaps** are the texture
pre-filtered at every half resolution, down to 1×1; the sampler picks the level
whose texels are about pixel-sized, and blends between the two nearest. The
whole chain costs one third more memory than the base level.

The number of levels for a `w × h` image is `floor(log2(max(w, h))) + 1`,
which C++20 spells `std::bit_width(std::max(w, h))`: a 256×256 texture has
nine (256, 128, …, 1). Non-square and non-power-of-two images work the same
way, each dimension halving and stopping at 1.

### How the sampler picks a level: 2×2 quads and derivatives

The sampler sees one texture coordinate per pixel, not the screen. It learns
how far apart neighbouring pixels are in the texture from the way GPUs run
fragment shaders: in **2×2 blocks of pixels, called quads**, the four running
the same instruction at the same moment. When a shader samples a texture, the
hardware subtracts this pixel's texture coordinate from its right-hand
neighbour's, and from the one below. That difference — how much `uv` changes
from one pixel to the next — is a **screen-space derivative**. Multiplied by
the texture's size it is texels per pixel, and the mip level is log2 of that.

Worked: on a 256×256 texture, if the pixel to the right has a `uv` larger by
1/64, one pixel steps across 256 / 64 = 4 texels, and log2 4 = 2 — level 2,
the 64×64 version, where one texel is about one pixel.

GLSL can ask for derivatives itself. `dFdx(v)` and `dFdy(v)` are how much any
value `v` changes to the next pixel across and down, and `fwidth(v)` is
`abs(dFdx(v)) + abs(dFdy(v))`, how much it changes across one pixel. Section
8's mip-level view asks the hardware which level it chose, with
`textureQueryLod`; Chapter 18 uses `fwidth` to make cutout edges exactly one
pixel wide.

One consequence matters soon. A pixel's neighbours need its coordinates, so a
pixel that stops early must keep running anyway: when section 11's cutout shader
throws a pixel away with `discard`, that pixel writes nothing but stays alive as
a **helper** for its quad, still computing the values its neighbours subtract.
The same happens along a triangle's edge, where a quad's pixels outside the
triangle run as helpers.

### Anisotropic filtering needs a device feature

Look at a textured floor at a glancing angle and each pixel covers a long,
thin strip of texture — many texels along one axis, a few along the other:

```text
 one screen pixel       its footprint on a receding floor
       [ ]      ──▶    [================]     16 texels long, 1 texel wide

 the level for 16 texels: blurry across the strip as well as along it
 the level for 1 texel:   sharp across, but aliasing along it
 anisotropic filtering:   up to 16 samples of the 1-texel level, spread along the strip
```

A mip level chosen for the long axis blurs the short one; one chosen for the
short axis aliases along the long one. **Anisotropic filtering** takes several
samples along the long axis instead. It is what keeps a receding floor sharp,
and it costs a device feature: `samplerAnisotropy`, one of the Vulkan 1.0
features that lives in `VkPhysicalDeviceFeatures2::features`.

Every desktop GPU has it. It is still checked and enabled explicitly, because
that is Chapter 02 section 5's rule: query what you need, enable exactly that.
Two edits to `VulkanInstance.cpp`:

```cpp
// Chapter 02 section 5, hasRequiredFeatures - the return statement grows (Chapter 15):
return features13.dynamicRendering == VK_TRUE
    && features13.synchronization2 == VK_TRUE
    && features.features.samplerAnisotropy == VK_TRUE;
```

```cpp
// Chapter 02 section 6, CreateDevice - enabledFeatures gains its 1.0 feature (Chapter 15):
VkPhysicalDeviceFeatures2 enabledFeatures{
    .sType    = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_FEATURES_2,
    .pNext    = &enable13,
    .features = { .samplerAnisotropy = VK_TRUE },
};
```

and in Chapter 02 section 5's `rejectionReason`, the message for that check names the new
feature, so a rejected GPU still says why:

```cpp
    if (!hasRequiredFeatures(device))                                 { return "no dynamicRendering, synchronization2, or samplerAnisotropy"; }
```

A sampler that asks for anisotropy on a device that did not enable the feature
is a validation error at `vkCreateSampler`.

### Building the chain by blitting

The levels are made **on the GPU, by blitting**: copy the decoded pixels into
level 0, then `vkCmdBlitImage` each level from the one above it, at half the
size, with linear filtering. That is a 2×2 box filter per level — not the best
downsampling filter there is, but correct, fast, and built in. Blitting needs
three format features — `BLIT_SRC`, `BLIT_DST`, and
`SAMPLED_IMAGE_FILTER_LINEAR` — which the spec makes mandatory for
`R8G8B8A8_UNORM` and `_SRGB`, the only two formats this chapter uploads, so
nothing is queried here; a new format would need a
`vkGetPhysicalDeviceFormatProperties` check first. Block-compressed formats
(BC7 and friends) cannot be blit *destinations* at all; their mip chains have
to come precomputed in the file, which is the real reason engines ship KTX2 or
DDS rather than PNG.

> **Jump:** every barrier so far covered a whole image — Chapter 04's
> `transitionImage` uses `VK_REMAINING_MIP_LEVELS`. Here one image is in
> several layouts at once: the level being read is `TRANSFER_SRC_OPTIMAL`,
> the level being written is `TRANSFER_DST_OPTIMAL`, and the finished levels
> above them are already `SHADER_READ_ONLY_OPTIMAL`. A barrier's
> `subresourceRange` picks which levels it applies to, and each level's layout
> is tracked separately. Keep a picture of a column of levels, each with its
> own state, and walk down it.

The barrier helper for one level is Chapter 04's helper with a narrower range.
It is file-scope in the new texture file, because nothing else needs it:

```cpp
// Source/PillowFort/VulkanGraphics/GpuTexture.cpp
// File scope, above the namespace block. Chapter 04's transitionImage, for ONE mip level -
// transitionImage always covers them all.
static void transitionMipLevel(VkCommandBuffer commandBuffer, VkImage image, uint32_t level,
                               VkImageLayout oldLayout, VkImageLayout newLayout,
                               VkPipelineStageFlags2 srcStage, VkAccessFlags2 srcAccess,
                               VkPipelineStageFlags2 dstStage, VkAccessFlags2 dstAccess)
{
    const VkImageMemoryBarrier2 barrier{
        .sType               = VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER_2,
        .srcStageMask        = srcStage,
        .srcAccessMask       = srcAccess,
        .dstStageMask        = dstStage,
        .dstAccessMask       = dstAccess,
        .oldLayout           = oldLayout,
        .newLayout           = newLayout,
        .srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED,
        .dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED,
        .image               = image,
        .subresourceRange    = { VK_IMAGE_ASPECT_COLOR_BIT, level, 1, 0, 1 },
    };
    const VkDependencyInfo dependency{
        .sType                   = VK_STRUCTURE_TYPE_DEPENDENCY_INFO,
        .imageMemoryBarrierCount = 1,
        .pImageMemoryBarriers    = &barrier,
    };
    vkCmdPipelineBarrier2(commandBuffer, &dependency);
}
```

The header follows Chapter 11's `GpuMesh.h` — a struct of handles, an upload
function that returns an empty struct (logged) on failure, and a destroy:

```cpp
// Source/PillowFort/VulkanGraphics/GpuTexture.h
#pragma once

#include "PillowFort/Scene/Material.h"
#include "PillowFort/VulkanGraphics/VulkanResources.h"

#include <vulkan/vulkan.h>
#include <vma/vk_mem_alloc.h>

namespace pf::vulkan_graphics {

struct GpuTexture
{
    VkImage       image      = VK_NULL_HANDLE;
    VmaAllocation allocation = VK_NULL_HANDLE;
    VkImageView   view       = VK_NULL_HANDLE;
    uint32_t      mipLevels  = 0;
};

// Uploads an 8-bit RGBA image (_SRGB or UNORM per image.srgb) with a full mip chain built on
// the GPU, and leaves every level in SHADER_READ_ONLY_OPTIMAL for fragment shaders.
// An empty GpuTexture, logged, on failure.
GpuTexture uploadTexture(VulkanContext& context, const scene::TextureImage& image);
void       destroyTexture(VulkanContext& context, GpuTexture& texture);

// A trilinear, anisotropic sampler for one pair of UsdUVTexture wrap modes.
VkSampler createMaterialSampler(VkDevice device, VkPhysicalDevice physicalDevice,
                                scene::TextureWrap wrapS, scene::TextureWrap wrapT);

} // namespace pf::vulkan_graphics
```

**This is `uploadTexture`.** Read its barriers against Chapter 04's three
questions — they are spelled out after the code, one by one.

```cpp
// Source/PillowFort/VulkanGraphics/GpuTexture.cpp, inside namespace pf::vulkan_graphics.
// Includes GpuTexture.h, VulkanBarriers.h, Log.h, <algorithm>, <bit>, <cstring>, and <format>.
GpuTexture uploadTexture(VulkanContext& context, const scene::TextureImage& source)
{
    // Both formats can be blitted and filtered linearly on every Vulkan device (section 5).
    const VkFormat format    = source.srgb ? VK_FORMAT_R8G8B8A8_SRGB : VK_FORMAT_R8G8B8A8_UNORM;
    const uint32_t mipLevels = std::bit_width(std::max(source.width, source.height));

    const VkImageCreateInfo imageInfo{
        .sType       = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO,
        .imageType   = VK_IMAGE_TYPE_2D,
        .format      = format,
        .extent      = { source.width, source.height, 1 },
        .mipLevels   = mipLevels,
        .arrayLayers = 1,
        .samples     = VK_SAMPLE_COUNT_1_BIT,
        .tiling      = VK_IMAGE_TILING_OPTIMAL,
        .usage       = VK_IMAGE_USAGE_TRANSFER_SRC_BIT    // each level is the blit source of the next
                     | VK_IMAGE_USAGE_TRANSFER_DST_BIT    // the copy, and every blit, write into it
                     | VK_IMAGE_USAGE_SAMPLED_BIT,
        .sharingMode   = VK_SHARING_MODE_EXCLUSIVE,
        .initialLayout = VK_IMAGE_LAYOUT_UNDEFINED,
    };
    const VmaAllocationCreateInfo allocationInfo{ .usage = VMA_MEMORY_USAGE_AUTO };

    GpuTexture texture{ .mipLevels = mipLevels };
    if (vmaCreateImage(context.allocator, &imageInfo, &allocationInfo,
                       &texture.image, &texture.allocation, nullptr) != VK_SUCCESS)
    {
        Log::error(std::format("vmaCreateImage failed for texture {}.", source.name).c_str());
        return {};
    }

    const VkDeviceSize size = source.pixels.size();
    AllocatedBuffer staging = createBuffer(context, size, VK_BUFFER_USAGE_TRANSFER_SRC_BIT, true);
    std::memcpy(staging.mapped, source.pixels.data(), static_cast<size_t>(size));
    vmaFlushAllocation(context.allocator, staging.allocation, 0, VK_WHOLE_SIZE);   // no-op if coherent

    immediateSubmit(context, [&](VkCommandBuffer commandBuffer) {
        // (1) Every level: from nothing to "a transfer is about to write you".
        transitionImage(commandBuffer, texture.image,
                        VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
                        VK_PIPELINE_STAGE_2_NONE, VK_ACCESS_2_NONE,
                        VK_PIPELINE_STAGE_2_COPY_BIT | VK_PIPELINE_STAGE_2_BLIT_BIT,
                        VK_ACCESS_2_TRANSFER_WRITE_BIT);

        const VkBufferImageCopy region{
            .imageSubresource = { VK_IMAGE_ASPECT_COLOR_BIT, 0, 0, 1 },
            .imageExtent      = { source.width, source.height, 1 },
        };
        vkCmdCopyBufferToImage(commandBuffer, staging.buffer, texture.image,
                               VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, 1, &region);

        int32_t width  = static_cast<int32_t>(source.width);
        int32_t height = static_cast<int32_t>(source.height);
        for (uint32_t level = 1; level < mipLevels; ++level)
        {
            // (2) The level above was just written - by the copy, or by the previous blit -
            //     and is about to be read.
            transitionMipLevel(commandBuffer, texture.image, level - 1,
                               VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,
                               VK_PIPELINE_STAGE_2_COPY_BIT | VK_PIPELINE_STAGE_2_BLIT_BIT,
                               VK_ACCESS_2_TRANSFER_WRITE_BIT,
                               VK_PIPELINE_STAGE_2_BLIT_BIT, VK_ACCESS_2_TRANSFER_READ_BIT);

            const int32_t nextWidth  = std::max(width / 2, 1);
            const int32_t nextHeight = std::max(height / 2, 1);
            const VkImageBlit blit{
                .srcSubresource = { VK_IMAGE_ASPECT_COLOR_BIT, level - 1, 0, 1 },
                .srcOffsets     = { { 0, 0, 0 }, { width, height, 1 } },
                .dstSubresource = { VK_IMAGE_ASPECT_COLOR_BIT, level, 0, 1 },
                .dstOffsets     = { { 0, 0, 0 }, { nextWidth, nextHeight, 1 } },
            };
            vkCmdBlitImage(commandBuffer,
                           texture.image, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,
                           texture.image, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
                           1, &blit, VK_FILTER_LINEAR);

            // (3) The level above is finished: hand it to the fragment shaders.
            transitionMipLevel(commandBuffer, texture.image, level - 1,
                               VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                               VK_PIPELINE_STAGE_2_BLIT_BIT, VK_ACCESS_2_NONE,
                               VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_SHADER_SAMPLED_READ_BIT);

            width  = nextWidth;
            height = nextHeight;
        }

        // (4) The last level was written and never read by a blit.
        transitionMipLevel(commandBuffer, texture.image, mipLevels - 1,
                           VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                           VK_PIPELINE_STAGE_2_COPY_BIT | VK_PIPELINE_STAGE_2_BLIT_BIT,
                           VK_ACCESS_2_TRANSFER_WRITE_BIT,
                           VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_SHADER_SAMPLED_READ_BIT);
    });
    destroyBuffer(context, staging);

    const VkImageViewCreateInfo viewInfo{
        .sType            = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO,
        .image            = texture.image,
        .viewType         = VK_IMAGE_VIEW_TYPE_2D,
        .format           = format,
        .subresourceRange = { VK_IMAGE_ASPECT_COLOR_BIT, 0, mipLevels, 0, 1 },
    };
    if (vkCreateImageView(context.device, &viewInfo, nullptr, &texture.view) != VK_SUCCESS)
    {
        Log::error(std::format("vkCreateImageView failed for texture {}.", source.name).c_str());
        destroyTexture(context, texture);
        return {};
    }
    return texture;
}

void destroyTexture(VulkanContext& context, GpuTexture& texture)
{
    vkDestroyImageView(context.device, texture.view, nullptr);   // null is a no-op
    vmaDestroyImage(context.allocator, texture.image, texture.allocation);
    texture = {};
}
```

The four barriers, each against the three questions:

| # | Q1: what waits for what | Q2: whose writes, whose caches | Q3: layout |
| --- | --- | --- | --- |
| 1 | Nothing came before — a new image — so the source is `NONE`. The copy (`COPY`) and every blit (`BLIT`) must wait for the transition. | `NONE` to flush. `TRANSFER_WRITE` is what the copy and blits are about to do. | `UNDEFINED` to `TRANSFER_DST_OPTIMAL`, all levels: the contents are about to be overwritten, so discarding them is right |
| 2 | The blit (`BLIT`) that reads level *n*−1 must wait for whatever wrote it: the copy for level 0, the previous blit for the rest — `COPY \| BLIT` | The write (`TRANSFER_WRITE`) must be made available, and visible to the blit's read (`TRANSFER_READ`). This is the barrier that, if omitted, blits a level before it exists: a chain of fading garbage | `TRANSFER_DST` to `TRANSFER_SRC`, one level |
| 3 | The layout change must wait for the blit to *finish reading* (`BLIT`), and the fragment shaders that sample later wait for it (`FRAGMENT_SHADER`) | A read leaves nothing to flush (`NONE`); the sampled read (`SHADER_SAMPLED_READ`) is made visible. The level's data was made available by barrier 2 — barrier 3 continues that chain through the blit stage | `TRANSFER_SRC` to `SHADER_READ_ONLY`, one level |
| 4 | The last level was written by the last blit — or, for a 1×1 image, by the copy — so `COPY \| BLIT` | `TRANSFER_WRITE` made available, `SHADER_SAMPLED_READ` visible | `TRANSFER_DST` to `SHADER_READ_ONLY`, one level |

Barriers (3) and (4) name the fragment shader although the frame that samples
the texture is a later submission: a barrier's second half reaches every later
command on the queue (Chapter 04 section 5), and `immediateSubmit`'s fence only
tells the CPU. Chapter 08's `uploadToImage` ends the same way.

Note the `vmaFlushAllocation` after the `memcpy`: the staging memory may not be
*coherent* (Chapter 08 section 7), and the flush is a no-op where it is.
Chapter 10's `WriteFrameData` does the same.

### Samplers, one per pair of wrap modes

Samplers are independent of images (Chapter 08 section 3), so one sampler per
*way of sampling* is enough, shared by every texture that samples that way.
Here the only thing that varies between material textures is the wrap mode —
four for `wrapS` times four for `wrapT` — so `SceneRenderer` creates all
sixteen up front and indexes them with `wrapS * 4 + wrapT`.

```cpp
// GpuTexture.cpp - file scope, above the namespace block.
static VkSamplerAddressMode addressMode(pf::scene::TextureWrap wrap)
{
    switch (wrap)
    {
    case pf::scene::TextureWrap::Repeat: return VK_SAMPLER_ADDRESS_MODE_REPEAT;
    case pf::scene::TextureWrap::Mirror: return VK_SAMPLER_ADDRESS_MODE_MIRRORED_REPEAT;
    case pf::scene::TextureWrap::Clamp:  return VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE;
    case pf::scene::TextureWrap::Black:  return VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_BORDER;
    }
    return VK_SAMPLER_ADDRESS_MODE_REPEAT;
}
```

```cpp
// GpuTexture.cpp, inside namespace pf::vulkan_graphics.
VkSampler createMaterialSampler(VkDevice device, VkPhysicalDevice physicalDevice,
                                scene::TextureWrap wrapS, scene::TextureWrap wrapT)
{
    VkPhysicalDeviceProperties properties{};
    vkGetPhysicalDeviceProperties(physicalDevice, &properties);

    const VkSamplerCreateInfo samplerInfo{
        .sType            = VK_STRUCTURE_TYPE_SAMPLER_CREATE_INFO,
        .magFilter        = VK_FILTER_LINEAR,
        .minFilter        = VK_FILTER_LINEAR,
        .mipmapMode       = VK_SAMPLER_MIPMAP_MODE_LINEAR,    // blend between the two nearest levels
        .addressModeU     = addressMode(wrapS),
        .addressModeV     = addressMode(wrapT),
        .addressModeW     = VK_SAMPLER_ADDRESS_MODE_REPEAT,   // 2D textures never use it
        .anisotropyEnable = VK_TRUE,                          // section 5's device feature
        .maxAnisotropy    = std::min(16.0f, properties.limits.maxSamplerAnisotropy),
        .minLod           = 0.0f,
        .maxLod           = VK_LOD_CLAMP_NONE,                // every level the view has
        .borderColor      = VK_BORDER_COLOR_FLOAT_TRANSPARENT_BLACK,   // USD's "black" is (0, 0, 0, 0)
    };
    VkSampler sampler = VK_NULL_HANDLE;
    if (vkCreateSampler(device, &samplerInfo, nullptr, &sampler) != VK_SUCCESS)
    {
        Log::error("vkCreateSampler failed for a material sampler.");
    }
    return sampler;
}
```

`maxAnisotropy` 16 is the usual ceiling and costs little on any desktop GPU;
the limit is read rather than assumed because the spec only guarantees 16 when
the feature exists, and a mobile part may report less.

### One white texture, and why that is enough

Every input in set 1 is bound to *some* texture, always — section 6 explains
why the shader never asks "is there a texture here". An untextured input binds
a 1×1 white texture, and its remap is scale 1, bias 0, so the texture
contributes exactly 1 and the material's constant does the work.

The normal is the input that looks as if it needs something else — the
traditional answer is a second default, a 1×1 "flat normal" texture of
(128, 128, 255). With UsdPreviewSurface's remap it does not: white sampled with
**scale (0, 0, 0, 0) and bias (0, 0, 1, 0)** *is* (0, 0, 1), exactly. The
(128, 128, 255) texture with the usual ×2 − 1 remap is (0.004, 0.004, 1) — not
quite flat, because 255 is odd and 0.5 is not a byte value. One default
texture, white, `UNORM` — white is white in either encoding.

---

## 6. Material parameters, in both languages

What the fragment shader reads from set 1's binding 0 is the material's
numbers, plus each texture's remap. It is a uniform block, so it follows
`std140` (Chapter 08 section 8), and it is built only from `vec4` and `float` so
that the C++ twin lays out identically. Both go into
`Shaders/Include/SharedShaderTypes.h` after `DrawData`'s asserts, with their
own asserts, and the closing brace of `namespace pf::shared` moves below them
— Chapter 11's pattern:

```c
/* Shaders/Include/SharedShaderTypes.h - Chapter 15. One UsdUVTexture's remap of its texel. */
struct TextureTransform
{
    vec4 scale;       /* value = texel * scale + bias, per channel */
    vec4 bias;
    vec4 channel;     /* scalar inputs: the connected output as a mask, (0, 1, 0, 0) for outputs:g */
};

/* Chapter 15. GLSL: MaterialBlock, std140, set 1 binding 0. One per material. */
struct MaterialParameters
{
    vec4  baseColor;            /*   0  linear rgb; 1 when a texture drives it */
    vec4  emissiveColor;        /*  16  linear rgb; 1 when a texture drives it */
    float metallic;             /*  32 */
    float roughness;            /*  36 */
    float occlusion;            /*  40 */
    float opacity;              /*  44 */
    float opacityThreshold;     /*  48  > 0: a cutout */
    float ior;                  /*  52 */
    float padding0;             /*  56 */
    float padding1;             /*  60 */
    TextureTransform baseColorMap;   /*  64 */
    TextureTransform emissiveMap;    /* 112 */
    TextureTransform normalMap;      /* 160 */
    TextureTransform metallicMap;    /* 208 */
    TextureTransform roughnessMap;   /* 256 */
    TextureTransform occlusionMap;   /* 304 */
    TextureTransform opacityMap;     /* 352 */
};                                   /* 400 */

#ifdef __cplusplus
    static_assert(sizeof(TextureTransform) == 48, "TextureTransform layout drifted.");
    static_assert(sizeof(MaterialParameters) == 400, "MaterialParameters layout drifted.");
    static_assert(offsetof(MaterialParameters, baseColorMap) == 64, "MaterialParameters alignment drifted.");
    static_assert(offsetof(MaterialParameters, opacityMap) == 352, "MaterialParameters alignment drifted.");
    }
#endif
```

Why is the eight-float block padded to 64? In `std140` a struct member aligns
to 16, so `baseColorMap` would start at 64 whether or not the padding is
written. Writing it makes the C++ struct agree without relying on that rule,
and the `static_assert` on 64 proves it.

**One multiply for every input.** The scene keeps UsdPreviewSurface's
semantics — a connected texture replaces the constant — but the shader
computes every input as `constant × remap(texel)`. Packing reconciles the two:
a textured input's constant becomes 1, an untextured input's texture is white
with an identity remap. Both cases then evaluate to the right value with the
same instructions, and the shader has no branch on "has a texture", which
matters both for clarity and because a branch per input per pixel is real cost.
This is the one function that encodes the rule:

```cpp
// SceneRenderer.cpp - file scope, above the namespace block. pf::scene::Material -> its GPU twin.
// UsdPreviewSurface: a connected texture REPLACES the constant. The shader always computes
// constant * (texel * scale + bias), so a textured input's constant becomes 1 here, and an
// untextured input samples white with the identity remap the TextureInput already holds.
static pf::shared::MaterialParameters packMaterial(const pf::scene::Material& material)
{
    auto textured  = [](const pf::scene::TextureInput& input) { return input.image != pf::scene::NO_TEXTURE; };
    auto transform = [](const pf::scene::TextureInput& input) {
        return pf::shared::TextureTransform{ input.scale, input.bias, input.channel };
    };

    pf::shared::MaterialParameters parameters{
        .baseColor        = textured(material.baseColorTexture) ? glm::vec4(1.0f) : material.baseColor,
        .emissiveColor    = glm::vec4(textured(material.emissiveTexture) ? glm::vec3(1.0f)
                                                                         : material.emissiveColor, 0.0f),
        .metallic         = textured(material.metallicTexture)  ? 1.0f : material.metallic,
        .roughness        = textured(material.roughnessTexture) ? 1.0f : material.roughness,
        .occlusion        = textured(material.occlusionTexture) ? 1.0f : material.occlusion,
        .opacity          = textured(material.opacityTexture)   ? 1.0f : material.opacity,
        .opacityThreshold = material.opacityThreshold,
        .ior              = material.ior,
        .padding0         = 0.0f,
        .padding1         = 0.0f,
        .baseColorMap     = transform(material.baseColorTexture),
        .emissiveMap      = transform(material.emissiveTexture),
        .normalMap        = transform(material.normalTexture),
        .metallicMap      = transform(material.metallicTexture),
        .roughnessMap     = transform(material.roughnessTexture),
        .occlusionMap     = transform(material.occlusionTexture),
        .opacityMap       = transform(material.opacityTexture),
    };
    if (!textured(material.normalTexture))
    {
        // White remapped to exactly (0, 0, 1): "no normal map" (section 5).
        parameters.normalMap = { glm::vec4(0.0f), glm::vec4(0.0f, 0.0f, 1.0f, 0.0f), glm::vec4(0.0f) };
    }
    return parameters;
}
```

---
## 7. Set 1: one descriptor set per material

The index contract's set 1 is **per material**: binding 0 the parameters
above, bindings 1 to 7 the seven textures, all read by the fragment shader.

| Binding | Type | GLSL name |
| --- | --- | --- |
| 0 | `UNIFORM_BUFFER` | `MaterialBlock { MaterialParameters material; }` |
| 1 | `COMBINED_IMAGE_SAMPLER` | `baseColorTexture` |
| 2 | `COMBINED_IMAGE_SAMPLER` | `emissiveTexture` |
| 3 | `COMBINED_IMAGE_SAMPLER` | `normalTexture` |
| 4 | `COMBINED_IMAGE_SAMPLER` | `metallicTexture` |
| 5 | `COMBINED_IMAGE_SAMPLER` | `roughnessTexture` |
| 6 | `COMBINED_IMAGE_SAMPLER` | `occlusionTexture` |
| 7 | `COMBINED_IMAGE_SAMPLER` | `opacityTexture` |

Why a set per material rather than per draw: a material is shared by many
draws, and its set is written once, at load, and never again. Why combined
image samplers rather than separate images and samplers: each texture has
exactly one way of being sampled (its wrap modes), so pairing them costs
nothing and keeps one binding per texture.

### The layout, the samplers, and the white texture

**This is `CreateMaterialResources`**, called by `Initialize` between
`CreateFrameResources` and `CreatePipelines`:

```cpp
// SceneRenderer.cpp, inside namespace pf::vulkan_graphics (Chapter 15).
InitializationResult SceneRenderer::CreateMaterialResources()
{
    // Set 1's shape: the parameters, then the seven textures, all read by the fragment shader.
    std::array<VkDescriptorSetLayoutBinding, 1 + MATERIAL_TEXTURE_COUNT> bindings{};
    for (uint32_t binding = 0; binding < bindings.size(); ++binding)
    {
        bindings[binding] = {
            .binding         = binding,
            .descriptorType  = binding == 0 ? VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER
                                            : VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER,
            .descriptorCount = 1,
            .stageFlags      = VK_SHADER_STAGE_FRAGMENT_BIT,
        };
    }
    const VkDescriptorSetLayoutCreateInfo layoutInfo{
        .sType        = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO,
        .bindingCount = static_cast<uint32_t>(bindings.size()),
        .pBindings    = bindings.data(),
    };
    if (vkCreateDescriptorSetLayout(m_context.device, &layoutInfo, nullptr, &m_materialSetLayout) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateDescriptorSetLayout failed for set 1.");
    }

    // One sampler per pair of wrap modes, indexed wrapS * 4 + wrapT.
    for (uint32_t s = 0; s < 4; ++s)
    {
        for (uint32_t t = 0; t < 4; ++t)
        {
            m_materialSamplers[s * 4 + t] = createMaterialSampler(
                m_context.device, m_context.physicalDevice,
                static_cast<scene::TextureWrap>(s), static_cast<scene::TextureWrap>(t));
            if (m_materialSamplers[s * 4 + t] == VK_NULL_HANDLE)
            {
                return InitializationResult::failure("Creating the material samplers failed.");
            }
        }
    }

    // What every untextured input samples (section 5).
    m_whiteTexture = uploadTexture(m_context, scene::TextureImage{
        .name = "White", .width = 1, .height = 1, .srgb = false, .pixels = { 255, 255, 255, 255 } });
    if (m_whiteTexture.view == VK_NULL_HANDLE)
    {
        return InitializationResult::failure("Uploading the white texture failed.");
    }
    return InitializationResult::success();
}
```

The mesh pipeline layout — Chapter 11's `CreatePipelines` — gains set 1:

```cpp
    // In CreatePipelines, where Chapter 11 builds m_meshLayout (Chapter 15): set 1 joins set 0.
    const VkDescriptorSetLayout setLayouts[] = { m_frameSetLayout, m_materialSetLayout };
    const VkPipelineLayoutCreateInfo layoutInfo{
        .sType                  = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
        .setLayoutCount         = 2,
        .pSetLayouts            = setLayouts,
        .pushConstantRangeCount = 1,
        .pPushConstantRanges    = &drawRange,
    };
```

### Pool sizing, when materials keep arriving

Chapter 08 sized a pool exactly, because it knew every set it would ever
allocate. `SceneRenderer` does not know how many materials its demo will add:
it serves every scene demo, and each calls `AddMaterial` one material at a
time, like `AddMesh`. The viewer happens to know its file's count before its
first call, but `SceneRenderer` would rather not make every caller find a total
up front. Two honest options:

- Count first, then make one pool of exactly that size. Correct, but every
  caller must know the final count before its first `AddMaterial`, and the
  pool is remade whenever the count changes.
- **A list of pools, each of a fixed size, adding one when the newest is
  full.** The cost is a few unused descriptors in the last pool.

This chapter does the second. A full pool can tell you so: since Vulkan 1.1,
`vkAllocateDescriptorSets` may refuse a set its pool has no room for, and it
then returns `VK_ERROR_OUT_OF_POOL_MEMORY` (or `VK_ERROR_FRAGMENTED_POOL`)
rather than failing in an undefined way, and that is the signal to make
another. It may also hand the set out anyway, and drivers differ: a pool one
descriptor short, met in Chapter 24's Appendix A, is refused by AMD's driver
and not by NVIDIA's or lavapipe, and the validation layer is silent either way.
The code below is right on all three, because it adds a pool only when an
allocation fails and relies on the failure for nothing else. No test scene
here comes near 64 materials, so to see a second pool made, set
`MATERIALS_PER_POOL` to 1 for one run on AMD's driver: every material then
takes a pool of its own, and the scene must look exactly the same.

Each pool's sizes follow from the layout: per material, one uniform buffer and
seven combined image samplers. Sixty-four materials per pool is arbitrary; any
size works, and larger means fewer pools.

```cpp
// SceneRenderer.cpp - file scope, above the namespace block (Chapter 15).
static constexpr uint32_t MATERIALS_PER_POOL = 64;
```

```cpp
// SceneRenderer.cpp, inside namespace pf::vulkan_graphics. VK_NULL_HANDLE, logged, on failure.
VkDescriptorSet SceneRenderer::AllocateMaterialSet()
{
    VkDescriptorSet set = VK_NULL_HANDLE;
    if (!m_materialPools.empty())
    {
        const VkDescriptorSetAllocateInfo allocateInfo{
            .sType              = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO,
            .descriptorPool     = m_materialPools.back(),
            .descriptorSetCount = 1,
            .pSetLayouts        = &m_materialSetLayout,
        };
        const VkResult result = vkAllocateDescriptorSets(m_context.device, &allocateInfo, &set);
        if (result == VK_SUCCESS) { return set; }
        if (result != VK_ERROR_OUT_OF_POOL_MEMORY && result != VK_ERROR_FRAGMENTED_POOL)
        {
            Log::error(std::format("vkAllocateDescriptorSets failed: {}", string_VkResult(result)).c_str());
            return VK_NULL_HANDLE;
        }
    }

    // The newest pool is full, or there is none yet: add one.
    const VkDescriptorPoolSize poolSizes[] = {
        { VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER,         MATERIALS_PER_POOL },
        { VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER, MATERIALS_PER_POOL * MATERIAL_TEXTURE_COUNT },
    };
    const VkDescriptorPoolCreateInfo poolInfo{
        .sType         = VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO,
        .maxSets       = MATERIALS_PER_POOL,
        .poolSizeCount = 2,
        .pPoolSizes    = poolSizes,
    };
    VkDescriptorPool pool = VK_NULL_HANDLE;
    if (vkCreateDescriptorPool(m_context.device, &poolInfo, nullptr, &pool) != VK_SUCCESS)
    {
        Log::error("vkCreateDescriptorPool failed for material sets.");
        return VK_NULL_HANDLE;
    }
    m_materialPools.push_back(pool);

    const VkDescriptorSetAllocateInfo allocateInfo{
        .sType              = VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO,
        .descriptorPool     = pool,
        .descriptorSetCount = 1,
        .pSetLayouts        = &m_materialSetLayout,
    };
    if (vkAllocateDescriptorSets(m_context.device, &allocateInfo, &set) != VK_SUCCESS)
    {
        Log::error("vkAllocateDescriptorSets failed in a new pool.");
        return VK_NULL_HANDLE;
    }
    return set;
}
```

### `AddTexture` and `AddMaterial`

**This is `AddTexture`** — one line of real work, because section 5 did it:

```cpp
uint32_t SceneRenderer::AddTexture(const scene::TextureImage& image)
{
    m_textures.push_back(uploadTexture(m_context, image));   // an empty GpuTexture on failure
    return static_cast<uint32_t>(m_textures.size() - 1);
}
```

A failed upload still takes its index, so indices keep meaning the same thing
on both sides; `AddMaterial` treats an empty texture like no texture.

**This is `AddMaterial`**, grown from Chapter 11's version, which only kept the
CPU copy. The parameters go into a small **host-visible** uniform buffer:
400 bytes, written once with a `memcpy`. A device-local buffer would be faster
to read, and would need a staging copy *and* a barrier from the copy to the
fragment shader's uniform read; host writes made before `vkQueueSubmit2` need
neither (Chapter 10's `WriteFrameData` rule). For a few hundred materials the
difference is not measurable.

```cpp
uint32_t SceneRenderer::AddMaterial(const scene::Material& material)
{
    m_materials.push_back(material);   // Chapter 11's CPU copy

    GpuMaterial gpu{ .cutout = material.opacityThreshold > 0.0f };

    const shared::MaterialParameters parameters = packMaterial(material);
    gpu.parameters = createBuffer(m_context, sizeof(parameters), VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT, true);
    if (gpu.parameters.buffer != VK_NULL_HANDLE)
    {
        std::memcpy(gpu.parameters.mapped, &parameters, sizeof(parameters));
        vmaFlushAllocation(m_context.allocator, gpu.parameters.allocation, 0, VK_WHOLE_SIZE);
    }
    gpu.set = AllocateMaterialSet();

    if (gpu.parameters.buffer != VK_NULL_HANDLE && gpu.set != VK_NULL_HANDLE)
    {
        // Each input's texture and sampler, or white and the repeat sampler when untextured.
        const scene::TextureInput* inputs[MATERIAL_TEXTURE_COUNT] = {
            &material.baseColorTexture, &material.emissiveTexture,  &material.normalTexture,
            &material.metallicTexture,  &material.roughnessTexture, &material.occlusionTexture,
            &material.opacityTexture,
        };
        std::array<VkDescriptorImageInfo, MATERIAL_TEXTURE_COUNT> images{};
        for (uint32_t slot = 0; slot < MATERIAL_TEXTURE_COUNT; ++slot)
        {
            const scene::TextureInput& input = *inputs[slot];
            const bool usable = input.image < m_textures.size() &&
                                m_textures[input.image].view != VK_NULL_HANDLE;
            const uint32_t sampler = static_cast<uint32_t>(input.wrapS) * 4 + static_cast<uint32_t>(input.wrapT);
            images[slot] = {
                .sampler     = usable ? m_materialSamplers[sampler] : m_materialSamplers[0],
                .imageView   = usable ? m_textures[input.image].view : m_whiteTexture.view,
                .imageLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
            };
        }

        const VkDescriptorBufferInfo bufferInfo{
            .buffer = gpu.parameters.buffer,
            .offset = 0,
            .range  = sizeof(shared::MaterialParameters),
        };
        std::array<VkWriteDescriptorSet, 1 + MATERIAL_TEXTURE_COUNT> writes{};
        writes[0] = {
            .sType           = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET,
            .dstSet          = gpu.set,
            .dstBinding      = 0,
            .descriptorCount = 1,
            .descriptorType  = VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER,
            .pBufferInfo     = &bufferInfo,
        };
        for (uint32_t slot = 0; slot < MATERIAL_TEXTURE_COUNT; ++slot)
        {
            writes[slot + 1] = {
                .sType           = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET,
                .dstSet          = gpu.set,
                .dstBinding      = slot + 1,
                .descriptorCount = 1,
                .descriptorType  = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER,
                .pImageInfo      = &images[slot],
            };
        }
        vkUpdateDescriptorSets(m_context.device, static_cast<uint32_t>(writes.size()), writes.data(), 0, nullptr);
    }
    else
    {
        Log::error(std::format("Material {} could not be created on the GPU.", material.name).c_str());
    }

    m_gpuMaterials.push_back(gpu);
    return static_cast<uint32_t>(m_materials.size() - 1);
}
```

A texture index the renderer has no texture for — a scene whose textures were
not uploaded first — falls back to white rather than reading past the end of
`m_textures`. That is why order matters in the demo: **textures before
materials**. Meshes are independent of both and can come before or after.

```cpp
// Demos/UsdViewer/UsdViewerDemo.cpp, in Setup, before Chapter 14's material loop (Chapter 15):
// the textures first, because a material's set points at them.
for (uint32_t texture = 0; texture < m_scene.TextureCount(); ++texture)
{
    m_sceneRenderer.AddTexture(m_scene.GetTexture(texture));
}
```

**This is `DestroyMaterialResources`**: everything `CreateMaterialResources`,
`AddTexture`, and `AddMaterial` made, in reverse. Destroying a pool frees every
set allocated from it, so the sets are never freed one by one. A null handle is
a no-op for every call here, which is what makes it safe after an `Initialize`
that failed half way.

```cpp
// SceneRenderer.cpp, inside namespace pf::vulkan_graphics (Chapter 15).
void SceneRenderer::DestroyMaterialResources()
{
    for (GpuMaterial& material : m_gpuMaterials)
    {
        destroyBuffer(m_context, material.parameters);
    }
    m_gpuMaterials.clear();
    for (VkDescriptorPool pool : m_materialPools)
    {
        vkDestroyDescriptorPool(m_context.device, pool, nullptr);   // frees its sets too
    }
    m_materialPools.clear();
    for (GpuTexture& texture : m_textures)
    {
        destroyTexture(m_context, texture);
    }
    m_textures.clear();
    destroyTexture(m_context, m_whiteTexture);
    for (VkSampler& sampler : m_materialSamplers)
    {
        vkDestroySampler(m_context.device, sampler, nullptr);
        sampler = VK_NULL_HANDLE;
    }
    vkDestroyDescriptorSetLayout(m_context.device, m_materialSetLayout, nullptr);
    m_materialSetLayout = VK_NULL_HANDLE;
}
```

Chapter 09's rule applies: switching demos runs `Teardown` and later `Setup`
again (and from Chapter 18, so does a sample-count change), so this runs, and
everything is uploaded again from the `Scene` the demo kept.

### Binding per draw

**This is `RecordDraws`' change.** Chapter 11's binds the pipeline and set 0
once per list, then the mesh's buffers whenever the mesh changes. Set 1 joins
the mesh as per-draw state: bound whenever the material changes. Two edits, both
in Chapter 11's `RecordDraws`. Beside `boundMesh`, before the loop:

```cpp
    uint32_t boundMaterial = UINT32_MAX;   // Chapter 15: no material bound yet
```

and inside the loop, right after the line that skips a mesh with no buffers:

```cpp
        // Chapter 15: a material that does not exist, or never reached the GPU (AddMaterial logged
        // why), has no set 1 to bind: the draw is skipped rather than drawn with a stale one.
        if (item.material >= m_gpuMaterials.size() || m_gpuMaterials[item.material].set == VK_NULL_HANDLE)
        {
            continue;
        }

        // Per material change: its set 1. Section 11 binds the material's own pipeline here too.
        if (item.material != boundMaterial)
        {
            vkCmdBindDescriptorSets(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, m_meshLayout,
                                    1, 1, &m_gpuMaterials[item.material].set, 0, nullptr);   // firstSet = 1
            boundMaterial = item.material;
        }
```

`firstSet = 1` binds the set into slot 1 and leaves set 0, bound once per list,
where it is.

Chapter 11 drew a missing material magenta, from the push constant's color. A
draw cannot do that any more without a set to bind, so it is skipped instead;
`AddMaterial` has already logged why. The push constant still carries Chapter
11's `baseColor`, which the shader below no longer reads — `DrawData` is
append-only, and Chapter 19 retires the per-draw push constant anyway.

---

## 8. A first textured shader, and the test scene

**This is `MaterialSet.glsl` and Part 1's `Mesh.frag.glsl`** — everything set 1
needs on the shader side, and the smallest shader that uses it: Chapter 11's
Lambert, with its color read through the material. It reads two of the seven
textures, base color and emission; Part 2 reads the rest.

### Set 1 in GLSL

Set 1's declarations go in an include, because the mesh shader is not their
only reader: Chapter 17 draws cutout leaves into the shadow map, and its caster
shader reads the same set.

```glsl
// Shaders/Include/MaterialSet.glsl - Chapter 15. Set 1, as section 7 lays it out. Included,
// never compiled on its own.
#ifndef PF_MATERIAL_SET_GLSL
#define PF_MATERIAL_SET_GLSL

#include "SharedShaderTypes.h"

layout(std140, set = 1, binding = 0) uniform MaterialBlock { MaterialParameters material; };
layout(set = 1, binding = 1) uniform sampler2D baseColorTexture;
layout(set = 1, binding = 2) uniform sampler2D emissiveTexture;
layout(set = 1, binding = 3) uniform sampler2D normalTexture;
layout(set = 1, binding = 4) uniform sampler2D metallicTexture;
layout(set = 1, binding = 5) uniform sampler2D roughnessTexture;
layout(set = 1, binding = 6) uniform sampler2D occlusionTexture;
layout(set = 1, binding = 7) uniform sampler2D opacityTexture;

// UsdUVTexture's output: texel * scale + bias. Colors use .rgb.
vec4 remap(vec4 texel, TextureTransform transform)
{
    return texel * transform.scale + transform.bias;
}

// A scalar input: the remapped texel's connected channel.
float remapScalar(vec4 texel, TextureTransform transform)
{
    return dot(remap(texel, transform), transform.channel);
}

#endif
```

`SharedShaderTypes.h` is included by both `FrameBlock.glsl` and this file; its
include guard makes the second inclusion empty.

### The fragment shader

The shader evaluates each input the way section 6 promised — `constant ×
remap(texel)`, with no branch on whether a texture is there — and lights the
result as Chapter 11 did. One debug view comes with it.
`ShadingMode::MipLevel` paints each pixel by the mip level its base color
texture is sampled at — `textureQueryLod` reports the level the hardware
chose, from section 5's derivatives — so the mip chain becomes visible: red is
level 0, then orange, yellow, green, cyan, blue, violet.

```glsl
// Shaders/Scene/Mesh.frag.glsl - Chapter 15, Part 1: the material's textures under Chapter 11's
// Lambert sun. Sections 9 and 11 grow it.
#version 450
#extension GL_GOOGLE_include_directive : require

#include "Color.glsl"        // srgbToLinear (Chapter 08 section 5), for the normals view
#include "FrameBlock.glsl"
#include "MaterialSet.glsl"

layout(location = 0) in vec3 worldPosition;
layout(location = 1) in vec3 worldNormal;
layout(location = 2) in vec2 uv;

layout(location = 0) out vec4 outColor;

layout(constant_id = 0) const uint shadingMode = 0;     // ShadingMode (Chapter 11)

const uint SHADING_LIT       = 0u;
const uint SHADING_NORMALS   = 1u;
const uint SHADING_MIP_LEVEL = 2u;

// A color per mip level: red is level 0, then orange, yellow, green, cyan, blue, violet.
vec3 mipLevelColor(float level)
{
    const vec3 colors[7] = vec3[](vec3(1.0, 0.0, 0.0), vec3(1.0, 0.5, 0.0), vec3(1.0, 1.0, 0.0),
                                  vec3(0.0, 1.0, 0.0), vec3(0.0, 1.0, 1.0), vec3(0.0, 0.0, 1.0),
                                  vec3(0.6, 0.0, 1.0));
    return colors[clamp(int(level + 0.5), 0, 6)];
}

void main()
{
    // Every input: constant * remap(texel) (section 6). Part 1 reads two of the seven.
    vec3 baseColor = material.baseColor.rgb * remap(texture(baseColorTexture, uv), material.baseColorMap).rgb;
    vec3 emissive  = material.emissiveColor.rgb * remap(texture(emissiveTexture, uv), material.emissiveMap).rgb;

    vec3 N = normalize(worldNormal);
    if (!gl_FrontFacing) { N = -N; }   // double-sided meshes light their back (Chapter 11)

    // Chapter 11's Lambert, with the color from set 1 instead of the push constant.
    float diffuse = max(dot(N, -frame.sunDirection.xyz), 0.0);
    vec3  color   = baseColor * (frame.sunColor.rgb * diffuse + frame.ambientColor.rgb) + emissive;

    // The normals view: decoded here, so that after the composite's encode the screen shows n * 0.5 + 0.5.
    if (shadingMode == SHADING_NORMALS)   { color = srgbToLinear(N * 0.5 + 0.5); }
    if (shadingMode == SHADING_MIP_LEVEL) { color = mipLevelColor(textureQueryLod(baseColorTexture, uv).x); }

    outColor = vec4(color, 1.0);
}
```

Untextured surfaces in the `MipLevel` view are red: they sample the 1×1 white
texture, whose only level is 0.

The new view needs a value and a button. `ShadingMode` gains `MipLevel = 2`
(the class map above) and `SHADING_MODE_COUNT` becomes 3, so Chapter 11's
`CreatePipelines` loop, which builds one pipeline per mode, builds the third
without being told. The viewer gets the button:

```cpp
// Demos/UsdViewer/UsdViewerDemo.cpp, DrawPanel: right after Chapter 14's "Normals" radio
// button (Chapter 15). The value is ShadingMode's.
ImGui::SameLine();
ImGui::RadioButton("Mip level", &shading, 2);
```

The viewer hands `m_shading` to the renderer in `Record`, as Chapter 11's
Meshes demo does, so a change shows on the next frame with nothing rebuilt.

### The test scene

`Assets/Scenes/MaterialTest.usda`, with four textures in
`Assets/Scenes/Textures/`. The file is written by hand and the textures by a
short script, `make_test_assets.py`; both are in the appendices, to copy rather
than read. Run the script once from `Assets/Scenes/`
(`python make_test_assets.py` — plain Python 3, standard library only) and
commit what it writes; it is not part of the build.

Each object in the scene tests one thing, with a value you can check. Part 1
uses three of them:

| Object | Tests | What to see |
| --- | --- | --- |
| `Floor` | Mipmaps, anisotropy, `repeat` | A 40 m checkerboard, 20 tiles each way, sharp near the camera and a smooth grey — not moiré — in the distance |
| `GreyBandsPanel` | Color space, `auto`, emission | Eight grey bands whose screen values are the texture's bytes exactly: 0, 32, 64, 96, 128, 160, 188, 255 |
| `MissingPanel` | A texture that does not exist | Magenta — the texture node's `fallback` — and a warning in the log |

The other two are Part 2's. Until then `BumpsPanel` is a flat grey panel and
`LeafPanel` a green rectangle.

`GreyBands` is the color check, and it is built to be exact. Its material's
`diffuseColor` is 0, so Lambert reflects nothing from it, and its emission is
the texture: the pixel is the emission alone. (It is also `metallic` 1, which
keeps it exact in Part 2: a black metal reflects nothing under any of section
9's models either.) The texture's bytes are sRGB; `auto` on an 8-bit RGBA file
makes it `_SRGB`; the sampler decodes to linear; the composite pass, which at
this point only clamps and encodes (Chapter 08 section 4), encodes back. Every
band comes out as the byte that went in. If the image had been created `UNORM`
instead, the 128 band would read 188 and the 64 band 137: encoded twice.

## Checkpoint

Run `UsdViewerDemo` on `MaterialTest.usda` with validation on. You can now
check:

- [ ] The scene loads with exactly one warning, naming
      `Textures/DoesNotExist.png`, and `MissingPanel` is magenta.
- [ ] **Color is right, to the byte.** Each of `GreyBandsPanel`'s eight bands
      reads back as its texture value — 0, 32, 64, 96, 128, 160, 188, 255 —
      within 1. (A pixel probe, RenderDoc's pixel history, or a screenshot in
      an image editor all do.)
- [ ] **Mipmaps are visible.** In "Mip level" the floor is red under the
      camera and steps through orange to yellow at its far edge, in bands
      across the view. In "Lit" the far floor stays a fine checker right to
      its edge, with no moiré, and it does not crawl when the camera moves.
- [ ] **Each half of that has a job.** Force `mipLevels` to 1 in
      `uploadTexture`, and the far floor breaks into moiré. Set
      `anisotropyEnable` to `VK_FALSE` in `createMaterialSampler`, and the far
      floor blurs to grey while the mip view runs on through green, cyan,
      blue, and violet: without anisotropy the level is chosen for the pixel's
      long axis, with it for the short one. Put both back.
- [ ] **The mip chain's barriers are proven.** Synchronization validation is
      silent through loading. Then weaken barrier (2), the one at the top of
      `uploadTexture`'s loop: change its destination access from
      `VK_ACCESS_2_TRANSFER_READ_BIT` to `VK_ACCESS_2_NONE`. The layer reports
      `SYNC-HAZARD-READ-AFTER-WRITE` on `vkCmdBlitImage`, once per level, while
      the textures load: the blit reads a level whose write was never made
      visible to it — the "chain of fading garbage" of the table above, caught
      before it can show. Put it back.
- [ ] Switching to another demo and back runs `Teardown` and `Setup` again:
      the scene reappears unchanged, with no validation errors, and
      `vmaDestroyAllocator` at shutdown reports nothing leaked.

---

# Part 2 — Surfaces (sections 9-13)

Part 1's surfaces are matte: every material is its texture under Chapter 11's
Lambert. Part 2 turns them into materials. Section 9 lays three shading models
side by side — Lambert, normalized Blinn-Phong, and the microfacet model
UsdPreviewSurface specifies — each as an equation and as code, with a switch to
flip between them live, and ends on a checkpoint where you do. Sections 10 and
11 add normal maps, which need a
tangent at every vertex, and cutouts, which need `discard`. At the end, metal
looks like metal, bumps catch the sun, and leaves have leaf-shaped edges.

---

## 9. Shading: three BRDFs, side by side

**This is `Shaders/Include/PreviewSurface.glsl`**, and the switch that picks
between its models. Part 1 lit every surface with Chapter 11's one line,
`baseColor × (sunColor × max(dot(N, L), 0) + ambient)`. That is the **Lambertian**
model — a perfectly matte surface — and it has no highlight at all: metal,
plastic, wet stone, and varnished wood all look the same under it. This section
writes it down properly, then adds two models that do have highlights: the
classic **normalized Blinn-Phong**, and the **microfacet** model
UsdPreviewSurface specifies. All three stay in the shader, behind one switch in
the viewer, so you can flip between them and see what each term buys.

> **Jump:** Chapter 11's shading was a formula you could read at a glance. From
> here a surface is described by a *BRDF* — a function that says how much of
> the light arriving from one direction leaves toward another — and the three
> models below are three BRDFs. Keep the structure in mind and the details will
> follow: **reflected = BRDF × incoming light × cos θ**, the same for all three;
> only the BRDF changes. Lambert's is a constant. The other two add a highlight
> built from a few named factors, each with an equation, a line of meaning, and
> its line of code.

### Two words for light, and four directions

Two quantities appear in every formula below, so here they are in plain words:

- **Radiance**, *L*, is what a camera pixel measures: how bright a surface looks
  from one direction. The shader's output color is a radiance. (Chapter 16
  section 2 makes this exact, with solid angles.)
- **Irradiance**, *E*, is how much light arrives on a surface: the power landing
  on each square metre of it. A light's irradiance is measured on a surface
  facing it. Tilt the surface by θ and the same beam spreads over more area, so
  it receives *E* cos θ — Chapter 11 section 14's Lambert cosine.

And four directions, all unit vectors pointing away from the shaded point:

```text
   l          n    h              v      n  the surface normal
     \        |   /           .-'        l  toward the light
       \      |  /        .-'            v  toward the eye
         \    | /     .-'                h  halfway between l and v: normalize(l + v)
           \  |/  .-'
   ───────────●─────────────── surface
```

The dot product of two of them is the cosine of the angle between them (Chapter
11 section 14), so **n**·**l** is 1 with the light overhead and 0 at the
horizon, and **n**·**h** is 1 when **h** lines up with the normal. Directions
are bold and lowercase because a capital *L* means radiance, here and in every
later chapter, and a plain *n* is (b)'s shininess below; the shader code names
them `N`, `L`, `V`, and `H`, as GLSL code usually does.

The BRDF, *f*, turns the light that arrives into the light that leaves toward
the eye:

$$
L_{\text{out}} = f \; E \; (\mathbf{n} \cdot \mathbf{l})
$$

Everything about the material lives in *f*, and one rule keeps it honest: a
surface cannot reflect more light than arrives.

### Where the code goes

`PreviewSurface.glsl` is an include, because the mesh shader is not its only
user: Chapter 16's light loop calls it once per light. Its head declares the
constants and the shading point. The functions of (a), (b), and (c) follow the
struct in this section's order, then `evaluatePreviewSurface` and
`evaluateAmbient`, then the `#endif`:

```glsl
// Shaders/Include/PreviewSurface.glsl - Chapter 15. Included, never compiled on its own
// (Chapter 06's glob compiles only Name.stage.glsl). Section 9's three BRDFs - Lambert,
// normalized Blinn-Phong, and GGX - and the two functions that light a surface with them.
#ifndef PF_PREVIEW_SURFACE_GLSL
#define PF_PREVIEW_SURFACE_GLSL

#include "SharedShaderTypes.h"   // BRDF_GGX, BRDF_BLINN_PHONG, BRDF_LAMBERT

const float PI            = 3.14159265358979;
const float MIN_ROUGHNESS = 0.05;   // see section 9: keeps the specular peak finite in half float

// One shading point, after its textures have been applied.
struct SurfaceSample
{
    vec3  baseColor;   // linear
    float metallic;
    float roughness;   // perceptual, as authored; squared below
    float ior;
    uint  brdf;        // BRDF_*: which model shades it - FrameData's, the same for every pixel
};

#endif
```

### (a) Lambert

A Lambertian surface scatters the light it does not absorb equally in every
direction, so it looks equally bright from wherever you look. Its BRDF is
therefore one number per color channel, the same for every **l** and **v**. Which
number? Not simply the **albedo** — the fraction of light the surface reflects,
`baseColor` — but the albedo divided by π, and the π comes from adding up a
sky.

Put a white surface under a uniformly bright sky of radiance *L*. Light from
overhead hits it square-on; light from near the horizon arrives at a slant and
counts for less, by the cosine. Adding up the whole sky, each direction
weighted by its cosine, gives an irradiance of exactly π × *L*. A white surface
should look exactly as bright as the sky that lights it, so *f* × π*L* = *L*,
and *f* = 1/π. For any albedo:

$$
f_{\text{Lambert}} = \frac{\text{albedo}}{\pi}
\qquad\qquad
L_{\text{out}} = \frac{\text{albedo}}{\pi} \; E \; (\mathbf{n} \cdot \mathbf{l})
$$

Worked: a grey floor of albedo 0.5, with the sun overhead delivering *E* = 3,
looks 0.5 / π × 3 = 0.48 from every direction. Chapter 16 section 2 uses the
same fact — a sky lights a surface with π times its radiance — for dome lights.

```glsl
// PreviewSurface.glsl - (a), after the struct.
// (a) Lambert: light leaves equally in every direction, so the BRDF is one number per channel.
vec3 lambertBrdf(SurfaceSample s)
{
    return s.baseColor / PI;
}
```

Chapter 11 folded that π into its light: its `sunColor` was defined as "what a
white surface facing the sun reflects", which is irradiance divided by π. So
the shader passes `π × sunColor` as the irradiance, and Lambert comes out
exactly as bright as Chapter 11.

### Microfacets: where highlights come from

Real surfaces are rough at a scale far below a pixel. Model them as countless
tiny mirrors — **microfacets** — each reflecting perfectly. A mirror reflects
**l** into **v** only if its normal is exactly **h**, so how bright a highlight
is toward **v** depends on how many facets face **h**. How spread out the
facets' directions are is one number, **α** (alpha). With a small α nearly
every facet faces **n**, and the surface is a near-mirror with a small, bright highlight; with a large α the
facets point every which way, and the highlight is a broad, dim sheen. The cone
of directions a surface sends one beam into is its **lobe**.

**Roughness, squared.** UsdPreviewSurface's `roughness` is *perceptual*: its
spec says it is "usually squared before use with a GGX lobe", and USD's own
viewer does exactly that, `α = roughness²`. Squaring spreads the useful range
evenly across the slider — without it, everything above 0.5 looks equally
matte. Both models below take this α.

They also share how much each facet reflects, which depends on what the surface
is made of and on the angle.

**F — Fresnel: how much a facet reflects.** Every surface becomes a mirror at
grazing angles — look across a lake. Schlick's approximation interpolates
between the head-on reflectance **F0** and the grazing one **F90**, by how far
the view is from head-on:

$$
F = F_0 + (F_{90} - F_0)\,(1 - \mathbf{v} \cdot \mathbf{h})^5
$$

The fifth power keeps F near F0 almost all the way to grazing. With F0 = 0.04
and F90 = 1: seen 60° from head-on, **v**·**h** = 0.5 and F = 0.04 + 0.96 × 0.5⁵ =
0.07; at 85°, **v**·**h** = 0.087 and F = 0.65.

**Metals and dielectrics: where F0 comes from.** The `metallic` input switches
between two kinds of material:

- **Dielectrics** (plastic, wood, stone, skin) reflect a little light at the
  surface, colorless, and the rest enters, scatters, and comes back out
  tinted — that is the diffuse part. Their head-on reflectance comes from the
  index of refraction: `F0 = ((ior − 1)/(ior + 1))²`, which is 0.04 for
  UsdPreviewSurface's default `ior` of 1.5.
- **Metals** reflect everything at the surface, tinted by the metal — gold's
  yellow is its reflection — and have no diffuse part at all.

UsdPreviewSurface blends the two by `metallic`, exactly as USD's own viewer
does: the reflection tint is `mix(1, baseColor, metallic)`, F0 is the
dielectric reflectance blended toward that tint, F90 is the tint, and the
diffuse part is scaled by `(1 − metallic)`. One more factor: light that
reflects at the surface does not also enter it, so the diffuse part is scaled
by `(1 − F)`.

```glsl
// PreviewSurface.glsl - shared by (b) and (c), after lambertBrdf.
// What the surface reflects head-on (f0) and at grazing angles (f90). USD's viewer's blend.
void fresnelEndpoints(SurfaceSample s, out vec3 f0, out vec3 f90)
{
    float r    = (1.0 - s.ior) / (1.0 + s.ior);           // 0.2 at ior 1.5: r * r = 0.04
    vec3  tint = mix(vec3(1.0), s.baseColor, s.metallic); // metals tint their reflection
    f0  = mix(r * r * tint, tint, s.metallic);
    f90 = tint;
}

// F: Schlick's Fresnel. How much a facet reflects, from f0 head-on up to f90 at grazing angles.
// The max: VdotH is at most 1 only in exact arithmetic. It is a dot of two normalized vectors, and
// where they nearly coincide a GPU's approximate normalize can put it a hair above 1; pow of a
// negative number is NaN.
vec3 schlickFresnel(vec3 f0, vec3 f90, float VdotH)
{
    return mix(f0, f90, pow(max(1.0 - VdotH, 0.0), 5.0));
}
```

### (b) Normalized Blinn-Phong

The oldest way to draw a highlight (Blinn, 1977) measures how close **h** is to
**n** and raises it to a power: (**n**·**h**)ⁿ. At **h** = **n** it is 1; away
from **n** it falls off,
the faster the larger the **shininess** n. That shape is a lobe of facet
directions, and a smooth surface has a large n.

The raw power has a flaw. As n grows the lobe narrows but its peak stays at 1,
so the total light it reflects shrinks: a smoother surface would look darker,
which no real material does. The fix is to divide by the lobe's total. Added up
over every direction, weighted by the cosine as in (a), (**n**·**h**)ⁿ comes to about
8π / (n + 8), so the factor in front is its reciprocal, (n + 8) / 8π. Every n
then reflects the same total: a narrow lobe gets a tall peak, a wide one a low
peak. With n = 30 the factor is 1.5; with n = 1248 it is 50.

The last piece maps roughness to shininess, so that one slider drives both
models:

$$
n = \frac{2}{\alpha^2} - 2
$$

That is the standard match between this lobe and a microfacet distribution of
width α, and it makes the two models' peaks agree: head-on, (c)'s peak below
comes to 1 / (4πα²), and (n + 8) / 8π with this n is (2/α² + 6) / 8π — the
same, give or take 0.24. Roughness 0.5 gives α = 0.25 and n = 30; roughness 0.2
gives n = 1248; roughness 1 gives n = 0, a flat lobe of 1/π.

The whole model is Lambert's diffuse, reduced by what the surface already
reflected at its top (1 − F) and switched off for metals (1 − *m*, with *m* the
`metallic` input), plus Fresnel times the normalized lobe:

$$
f_{\text{Blinn-Phong}} = (1 - F)(1 - m)\,\frac{\text{albedo}}{\pi} \;+\; F\,\frac{n + 8}{8\pi}\,(\mathbf{n} \cdot \mathbf{h})^n
$$

```glsl
// PreviewSurface.glsl - (b), after schlickFresnel.
// (b) Normalized Blinn-Phong: the lobe (N.H)^n, scaled so it reflects the same total light at
// every width. n from alpha gives the same peak as GGX, so one roughness drives both.
float blinnPhongLobe(float NdotH, float alpha)
{
    float n = max(2.0 / (alpha * alpha) - 2.0, 1e-4);   // shininess; above 0, so pow(0, n) is defined
    return (n + 8.0) / (8.0 * PI) * pow(NdotH, n);
}
```

The `max` keeps n above zero: at roughness 1, n is exactly 0, and GLSL leaves
`pow(0, 0)` undefined.

### (c) The microfacet BRDF: GGX

UsdPreviewSurface specifies the model most renderers ship, and USD's own
viewer implements it. Its highlight asks three questions of the facets and
divides by one correction:

$$
f_{\text{specular}} = \frac{D \; G \; F}{4\,(\mathbf{n} \cdot \mathbf{l})(\mathbf{n} \cdot \mathbf{v})}
$$

Each factor answers one question:

- **D — distribution: how many facets face h.** The GGX (Trowbridge-Reitz)
  distribution:

  $$
  D = \frac{\alpha^2}{\pi\,\big((\mathbf{n} \cdot \mathbf{h})^2\,(\alpha^2 - 1) + 1\big)^2}
  $$

  Its peak, at **n**·**h** = 1, is 1 / (πα²): 199 for roughness 0.2, 5.1 for 0.5, and
  0.32 for 1.0. That is "a tall spike when smooth, a broad low lobe when rough"
  in numbers. Away from its peak GGX falls off more slowly than Blinn-Phong's
  lobe — a long tail that gives highlights a soft glow around their core, which
  real materials have, and the reason GGX is everyone's choice.

- **G — geometry: how many of those facets are visible from both l and v.** On
  a rough surface, facets shadow and hide one another at grazing angles.
  Smith's model treats the two directions separately and multiplies, with
  Schlick's approximation of each:

  $$
  G = G_1(\mathbf{n} \cdot \mathbf{v})\;G_1(\mathbf{n} \cdot \mathbf{l}), \qquad G_1(x) = \frac{x}{x\,(1 - k) + k}, \qquad k = \frac{\alpha}{2}
  $$

  G is 1 head-on and falls toward 0 at grazing angles, faster for rougher
  surfaces.

- **F — Fresnel**, as above: how much each facet reflects.

- **4 (n·l)(n·v)** is a correction factor that falls out of the derivation and
  keeps the total reflected energy right; take it as given. What it does is
  visible: at grazing angles **n**·**v** is small, so the highlight grows — and G holds
  it back.

The diffuse part is (b)'s, so the whole model is

$$
f_{\text{GGX}} = (1 - F)(1 - m)\,\frac{\text{albedo}}{\pi} \;+\; \frac{D \; G \; F}{4\,(\mathbf{n} \cdot \mathbf{l})(\mathbf{n} \cdot \mathbf{v})}
$$

```glsl
// PreviewSurface.glsl - (c), after blinnPhongLobe.
// (c) D: GGX (Trowbridge-Reitz). The share of microfacets facing the half vector.
float ggxDistribution(float NdotH, float alpha)
{
    float alpha2 = alpha * alpha;
    float d      = NdotH * NdotH * (alpha2 - 1.0) + 1.0;
    return alpha2 / (PI * d * d);
}

// (c) G: Smith, Schlick-GGX form, k = alpha / 2. The share visible from both directions.
float smithGeometry(float NdotV, float NdotL, float alpha)
{
    float k = alpha * 0.5;
    return (NdotV / (NdotV * (1.0 - k) + k)) * (NdotL / (NdotL * (1.0 - k) + k));
}
```

**A floor under roughness.** At roughness 0, GGX's peak, 1 / (πα²), divides by
zero: an infinitely tall spike of no width. Under a point-like light the
highlight becomes one pixel of a value larger than the scene target can hold —
`R16G16B16A16_SFLOAT` tops out at 65504, and anything beyond is infinity, which
the composite pass turns into NaN. So roughness is clamped to 0.05,
`MIN_ROUGHNESS`, before squaring: the peak is then 1 / (π × 0.0025²) ≈ 51 000,
large but finite, and the final color is clamped to 64000 as well. Blinn-Phong
goes through the same clamp, so the switch never changes which values are
finite.

### Putting the three together

**This is `evaluatePreviewSurface`**: one light's contribution, by whichever
model `s.brdf` names. Lambert needs only **n**·**l**, so it returns first; the other two
share **h**, α, and F, and differ only in the highlight:

```glsl
// PreviewSurface.glsl, after smithGeometry.
// Radiance reflected toward V from one light arriving along L, whose irradiance on a surface
// facing it is `irradiance`. N, V, L: unit vectors in world space, V and L pointing away from
// the surface. s.brdf picks the model; it is the same for every pixel, so the branch is uniform.
vec3 evaluatePreviewSurface(SurfaceSample s, vec3 N, vec3 V, vec3 L, vec3 irradiance)
{
    float NdotL = dot(N, L);
    if (NdotL <= 0.0) { return vec3(0.0); }               // the light is behind the surface
    if (s.brdf == BRDF_LAMBERT) { return lambertBrdf(s) * irradiance * NdotL; }   // (a)

    float NdotV = max(dot(N, V), 1e-4);
    vec3  H     = normalize(V + L);
    float NdotH = max(dot(N, H), 0.0);
    float VdotH = max(dot(V, H), 0.0);

    float roughness = max(s.roughness, MIN_ROUGHNESS);
    float alpha     = roughness * roughness;

    vec3 f0;
    vec3 f90;
    fresnelEndpoints(s, f0, f90);
    vec3 F = schlickFresnel(f0, f90, VdotH);

    vec3 specular;
    if (s.brdf == BRDF_BLINN_PHONG)
    {
        specular = F * blinnPhongLobe(NdotH, alpha);                                         // (b)
    }
    else
    {
        specular = F * ggxDistribution(NdotH, alpha) * smithGeometry(NdotV, NdotL, alpha)
                 / (4.0 * NdotL * NdotV);                                                     // (c)
    }
    vec3 diffuse = (1.0 - F) * (1.0 - s.metallic) * s.baseColor / PI;
    return (diffuse + specular) * irradiance * NdotL;
}
```

**Why a branch on the model costs almost nothing.** A GPU runs pixels in
groups — 32 or 64 at a time on desktop GPUs, called a *warp* or a *wave* — that
execute one instruction stream together. A branch is expensive only when the
pixels in one group disagree: then the group runs both sides, each pixel
keeping its own result. `s.brdf` comes from `FrameData`, one value for the whole
frame, so every pixel takes the same side — the branch is *uniform* — and its
cost is one comparison. A specialization constant would compile the choice away
entirely, but it would need a pipeline per model and would exist only in this
renderer's pipelines. In `FrameData`, Chapter 22's deferred lighting pass reads
the same field, so one switch drives both ways of rendering.

### Ambient, and what occlusion means

Chapter 11's `ambientColor` stands for light arriving from everywhere at once —
the sky, the walls. Done properly that is **image-based lighting**: an
environment map, prefiltered per roughness, and a lookup table for the
specular integral, as USD's own viewer does for its DomeLight. That is
Chapter 24's subject. Here ambient stays a constant, and a material receives it
through its diffuse color plus its head-on reflectance F0 — without that F0
term a polished metal, which has no diffuse part, would be black wherever the
sun does not reach.

`occlusion` darkens that ambient light only. An occlusion map records how much
of the sky each point can see — the inside of a crease, very little — which is
a statement about light from *everywhere*, not about the sun, whose shadows
Chapter 17 computes properly. (USD's own viewer multiplies direct light by it
too; the spec does not say, and this renderer takes the physical reading.)

```glsl
// PreviewSurface.glsl, after evaluatePreviewSurface: the last function before the #endif.
// Constant light from every direction: the diffuse part plus the head-on reflection. A stand-in
// for image-based lighting (section 9); `occlusion` darkens it, and only it. Lambert has no
// reflection, so it gets Chapter 11's baseColor * ambient.
vec3 evaluateAmbient(SurfaceSample s, vec3 ambient, float occlusion)
{
    if (s.brdf == BRDF_LAMBERT) { return ambient * occlusion * s.baseColor; }
    vec3 f0;
    vec3 f90;
    fresnelEndpoints(s, f0, f90);
    return ambient * occlusion * ((1.0 - f0) * (1.0 - s.metallic) * s.baseColor + f0);
}
```

Under Lambert the ambient light is Chapter 11's `baseColor × ambient`: Lambert
has no Fresnel, so nothing is reflected at the surface itself.

### Switching between them live

The choice travels in `FrameData`, set 0's per-frame block, which every pixel of
every draw can read. `FrameData` is append-only (Chapter 10 section 7), so the
field goes at its end, padded to the 16 bytes a `std140` struct is rounded up
to. Its values are defines, so C++ and GLSL share them.

In `SharedShaderTypes.h`, just above `struct FrameData`:

```c
/* Chapter 15: FrameData::brdf, the model that shades every surface (section 9). 0 is GGX, so a
   FrameData that is zeroed and never told otherwise - every demo's - gets the default. */
#define BRDF_GGX         0u
#define BRDF_BLINN_PHONG 1u
#define BRDF_LAMBERT     2u
```

and at the end of `FrameData`, after Chapter 11's `ambientColor`:

```c
    /* Chapter 15: which BRDF shades every surface, the same for every pixel. */
    uint  brdf;             /* 272  BRDF_*; 0 is GGX */
    uint  padding2;         /* 276  keeps the size a multiple of 16 */
    uint  padding3;         /* 280 */
    uint  padding4;         /* 284 */
```

The asserts follow, the size to 288 and one more offset:

```c
#ifdef __cplusplus
    static_assert(sizeof(FrameData) == 288, "FrameData layout drifted.");
    static_assert(offsetof(FrameData, cameraPosition) == 192, "FrameData alignment drifted.");
    static_assert(offsetof(FrameData, time) == 208, "FrameData alignment drifted.");
    static_assert(offsetof(FrameData, sunDirection) == 224, "FrameData alignment drifted.");
    static_assert(offsetof(FrameData, brdf) == 272, "FrameData alignment drifted.");
#endif
```

Why GGX is 0: every demo builds its `FrameData` as `shared::FrameData
frameData{}`, which zeroes it, and fills only the fields it uses. A demo that
never mentions the BRDF must get the default, so the default is zero.

The USD viewer owns the setting, and shows it under its shading views:

```cpp
// Demos/UsdViewer/UsdViewerDemo.h, private, beside m_shading (Chapter 15).
uint32_t m_brdf = BRDF_GGX;   // Chapter 15 section 9: FrameData::brdf
```

```cpp
        // Demos/UsdViewer/UsdViewerDemo.cpp, DrawPanel: after the shading radio buttons (Chapter 15).
        // Chapter 15 section 9: the BRDF every surface is shaded with, carried by FrameData.
        int brdf = static_cast<int>(m_brdf);
        ImGui::TextUnformatted("BRDF:");
        ImGui::SameLine();
        ImGui::RadioButton("Lambert", &brdf, BRDF_LAMBERT);
        ImGui::SameLine();
        ImGui::RadioButton("Blinn-Phong", &brdf, BRDF_BLINN_PHONG);
        ImGui::SameLine();
        ImGui::RadioButton("GGX", &brdf, BRDF_GGX);
        m_brdf = static_cast<uint32_t>(brdf);
```

```cpp
// Demos/UsdViewer/UsdViewerDemo.cpp, Record: after Chapter 11's frameData.ambientColor (Chapter 15).
frameData.brdf           = m_brdf;   // Chapter 15 section 9
```

The mesh shader hands the value to the BRDF in one line, `s.brdf = frame.brdf`
(below). Flipping the switch rebuilds nothing: the next frame is simply
shaded by the other model.

### A check against Chapter 11

Under GGX, for a white dielectric facing the sun head-on, the diffuse term is
`(1 − 0.04) × baseColor × sunColor` — within 4% of Chapter 11 — and the ambient
term is `(0.96 × baseColor + 0.04) × ambient`, within 1%. Switching models does
not change how bright a matte scene is; it adds the highlights. Under Lambert it
is Chapter 11 exactly.

### The three on screen, before the normal maps

Section 11 rewrites the mesh fragment shader for normal maps and cutouts. The
three models need neither, so Part 1's shader can use them now, and you can
see what this section built before reading on. In `Mesh.frag.glsl`, include the
new file after `MaterialSet.glsl`:

```glsl
#include "PreviewSurface.glsl"
```

In `main()`, the comment "Chapter 11's Lambert" and the two lines under it,
`diffuse` and `color`, become the surface sample and one call to each function
above, still with Chapter 11's one sun:

```glsl
    // For now (section 9): the material's BRDF under Chapter 11's sun. Section 11 replaces main() whole.
    SurfaceSample s;
    s.baseColor = baseColor;
    s.metallic  = material.metallic  * remapScalar(texture(metallicTexture,  uv), material.metallicMap);
    s.roughness = material.roughness * remapScalar(texture(roughnessTexture, uv), material.roughnessMap);
    s.ior       = material.ior;
    s.brdf      = frame.brdf;   // section 9's choice, the same for every pixel
    float occlusion = material.occlusion * remapScalar(texture(occlusionTexture, uv), material.occlusionMap);

    // One sun, as in Chapter 11. sunColor is irradiance / pi (section 9).
    vec3 V = normalize(frame.cameraPosition.xyz - worldPosition);
    vec3 L = -frame.sunDirection.xyz;
    vec3 color = evaluatePreviewSurface(s, N, V, L, PI * frame.sunColor.rgb)
               + evaluateAmbient(s, frame.ambientColor.rgb, occlusion)
               + emissive;
```

and the last line clamps, for the reason "A floor under roughness" gave:

```glsl
    outColor = vec4(min(color, vec3(64000.0)), 1.0);
```

## Checkpoint

Build, and open `MaterialSweep.usda` in the viewer — Appendix B's script wrote
it in section 8: two rows of five spheres, roughness 0, 0.25, 0.5, 0.75, and 1
from left to right, grey plastic in front and gold behind. You can now check:

- [ ] **The roughness sweep.** Under GGX the plastic spheres' highlight goes
      from a small bright point (left) to a broad dim sheen (right); the gold
      spheres are gold-tinted mirrors on the left and satin on the right, and
      no sphere is black on its unlit side.
- [ ] **Three BRDFs, side by side.** Flip the viewer's BRDF switch. *Lambert*:
      no highlight on any sphere, and the gold row is yellow paint.
      *Blinn-Phong*: highlights in the same places as GGX's, but each fades to
      nothing at its edge, and the roughness-0 plastic sphere's pinpoint all
      but vanishes; the roughest gold spheres come out brighter, because
      nothing in Blinn-Phong shadows or hides facets (it has no G). *GGX*:
      every highlight has a soft glow around its core — the long tail. Then
      set the sun's Azimuth to 180 and its Elevation to 8, behind the spheres.
      Under GGX the smooth spheres' upper rims show a bright white crescent —
      Fresnel at a grazing angle, with the 4 (**n**·**l**)(**n**·**v**) term —
      under Blinn-Phong a dimmer one, and under Lambert only a dim grey edge.
- [ ] `MaterialTest.usda` under Lambert looks as it did at Part 1's checkpoint,
      and `GreyBandsPanel` reads its exact bytes under all three models: a
      black metal reflects nothing, so its pixel is its emission alone.

---

## 10. Tangents

A normal map stores, per texel, which way the surface *really* faces — but not
in world space, which would tie the texture to one object in one pose. It
stores the direction relative to the texture itself: red is "toward +u",
green is "toward +v as the image is drawn", blue is "straight out of the
surface". The shader has to know which world-space directions those are at the
point it is shading. The normal gives it one; it needs the other two.

That pair — the world-space directions in which the texture's u and v increase
— is the **tangent** and **bitangent**. They are a property of how the texture
was laid onto the mesh, so they come from the texture coordinates, and they
differ per vertex.

```text
             B: "up the image"
             ▲
   ┌─────────┼─────────┐
   │         │         │        N: out of the page, toward you
   │         ●───────▶ T: "right along the image", +u
   │                   │
   └───────────────────┘
      one textured quad, seen from the front
```

A texel whose normal says "straight out" is (0, 0, 1), stored as
(128, 128, 255) after the usual × 0.5 + 0.5. Most of a surface points mostly
straight out, which is why normal maps are mostly lavender-blue.

> **Jump:** a vertex has had one direction attached to it so far, the normal.
> From here it has a whole frame — tangent, bitangent, normal — and the normal
> map's colors are coordinates *in that frame*. Hold onto this: whenever a
> normal-mapped surface lights from the wrong side, the question is which of
> the three axes disagrees with the convention the texture was painted in.
> Section 11 has the shader half, and the exit check has the test that tells
> you.

**Deriving it** — optional; the code below is all you need. Take one triangle
with corners p0, p1, p2 and texture coordinates t0, t1, t2. Its edges in space
and in the texture are

```text
e1 = p1 - p0        d1 = t1 - t0 = (du1, dv1)
e2 = p2 - p0        d2 = t2 - t0 = (du2, dv2)
```

Across a flat triangle, position is a linear function of texture coordinate:
there are vectors T and B with `e1 = du1 T + dv1 B` and `e2 = du2 T + dv2 B`.
T is how far you move in space per unit of u — the tangent — and B per unit of
v. Two equations, two unknowns; solving them:

```text
r = 1 / (du1 dv2 - du2 dv1)
T = r (dv2 e1 - dv1 e2)
B = r (du1 e2 - du2 e1)
```

Each vertex accumulates T and B from every triangle that uses it. Leaving the
per-triangle vectors unnormalized weights big triangles more, which is what
you want. Then, per vertex, **Gram–Schmidt**: subtract the part of T along the
normal, so the frame is orthogonal, and normalize.

The bitangent is not stored — it is recomputed in the shader as
`cross(N, T)` (Chapter 12 section 5). What that cross product cannot know is
whether the texture was *mirrored* — artists mirror UV islands all the time, to
paint one ear for two. So the vertex keeps one bit of B: its sign relative to
`cross(N, T)`, in `tangent.w`. That is the `w` the index contract reserved in
Chapter 11's `Vertex`.

**The convention.** Blender, USD, and the OpenGL tradition paint normal maps
with green pointing **up the image**. Chapter 14 flipped texture coordinates
into the engine's convention, `v_engine = 1 − v_usd`, so the engine's `v` grows
*down* the image. The bitangent the shader needs is therefore "toward
decreasing `v`", and the function below negates the `v` differences before
solving. Get this sign wrong and every bump is lit from below — which the exit
check catches.

```cpp
// Source/PillowFort/Scene/Tangents.h
#pragma once

#include "PillowFort/Scene/MeshData.h"

namespace pf::scene {

// Fills every vertex's tangent from positions, normals, and texture coordinates: xyz is the
// direction in which u increases, w the sign that turns cross(normal, tangent) into the
// direction in which the image's "up" increases. Every vertex gets a unit tangent
// perpendicular to its normal, even where the texture coordinates are degenerate.
void generateTangents(MeshData& mesh);

} // namespace pf::scene
```

```cpp
// Source/PillowFort/Scene/Tangents.cpp, inside namespace pf::scene. Includes Tangents.h,
// <glm/glm.hpp>, <cmath>, and <vector>.
void generateTangents(MeshData& mesh)
{
    std::vector<glm::vec3> tangents(mesh.vertices.size(), glm::vec3(0.0f));
    std::vector<glm::vec3> bitangents(mesh.vertices.size(), glm::vec3(0.0f));

    for (size_t i = 0; i + 2 < mesh.indices.size(); i += 3)
    {
        const uint32_t corner[3] = { mesh.indices[i], mesh.indices[i + 1], mesh.indices[i + 2] };
        const Vertex& v0 = mesh.vertices[corner[0]];
        const Vertex& v1 = mesh.vertices[corner[1]];
        const Vertex& v2 = mesh.vertices[corner[2]];

        const glm::vec3 e1 = v1.position - v0.position;
        const glm::vec3 e2 = v2.position - v0.position;
        // v is negated: the engine's v grows DOWN the image, and normal maps' green points UP it.
        const float du1 = v1.uv.x - v0.uv.x, dv1 = -(v1.uv.y - v0.uv.y);
        const float du2 = v2.uv.x - v0.uv.x, dv2 = -(v2.uv.y - v0.uv.y);

        const float determinant = du1 * dv2 - du2 * dv1;
        if (std::abs(determinant) < 1e-12f) { continue; }   // no usable texture mapping on this triangle

        const float r = 1.0f / determinant;
        const glm::vec3 t = r * (dv2 * e1 - dv1 * e2);
        const glm::vec3 b = r * (du1 * e2 - du2 * e1);
        for (uint32_t index : corner)
        {
            tangents[index]   += t;
            bitangents[index] += b;
        }
    }

    for (size_t i = 0; i < mesh.vertices.size(); ++i)
    {
        Vertex& vertex = mesh.vertices[i];
        const glm::vec3 n = vertex.normal;

        // Gram-Schmidt: remove the part along the normal.
        glm::vec3 t = tangents[i] - n * glm::dot(n, tangents[i]);
        if (glm::dot(t, t) < 1e-12f)
        {
            // Nothing usable accumulated: any direction perpendicular to the normal will do,
            // and keeps the shader from normalizing a zero vector.
            const glm::vec3 axis = std::abs(n.x) < 0.9f ? glm::vec3(1, 0, 0) : glm::vec3(0, 1, 0);
            t = glm::cross(axis, n);
        }
        t = glm::normalize(t);

        const float handedness = glm::dot(glm::cross(n, t), bitangents[i]) < 0.0f ? -1.0f : 1.0f;
        vertex.tangent = glm::vec4(t, handedness);
    }
}
```

Two callers, so that **every** mesh that reaches the GPU has tangents. In the
importer, the one funnel every imported mesh and shape passes through is
Chapter 14's `addMesh`; its texture coordinates are already flipped there.
`UsdImport.cpp` gains `#include "PillowFort/Scene/Tangents.h"` beside its own
includes, and:

```cpp
// UsdImport.cpp, the first line of addMesh (Chapter 15). `data` is its MeshData parameter.
pf::scene::generateTangents(data);
```

Calling it before Chapter 14's winding fix is fine: swapping two corners of a
triangle swaps both edges and both texture-coordinate differences, which flips
the sign of the determinant and of the numerators together, so T and B come
out the same. And the procedural meshes:

```cpp
// In Scene/MeshGenerators.cpp: the last line of makeCube, makeUvSphere, and makePlane,
// before `return mesh;` (Chapter 15). Includes "PillowFort/Scene/Tangents.h".
generateTangents(mesh);
```

The vertex split Chapter 14 does for face-varying normals and texture
coordinates matters here: a vertex on a UV seam is two vertices, each with its
own coordinates, so each gets the tangent of its own side of the seam.

**Why not read tangents from the file?** USD has no standard tangent primvar,
and Blender does not export one. In practice you compute them.

**Baked normal maps** assume the tangents of the tool that baked them; a
renderer whose tangents differ shows faint seams and lumps where the bake was
meant to be smooth. The industry standard is Morten Mikkelsen's
**MikkTSpace**, which Blender and the major engines implement, and TinyUSDZ
carries its reference implementation in `src/external/mikktspace`. The
function above agrees with it on well-behaved meshes; swap MikkTSpace in behind
`generateTangents` when baked assets show seams.

---

## 11. The mesh shaders, rewritten

**This is Part 2's half of `Mesh.vert.glsl`, `Mesh.frag.glsl`, and
`MaterialSet.glsl`, the device feature `discard` needs, and the cutout
pipelines.**

### The vertex shader

The tangent has been in every vertex since Chapter 11 — the 48-byte `Vertex`
and its stride never changed — but not in the pipeline's **vertex input**:
Chapter 11's `meshVertexAttributes()` describes locations 0 to 2 only. That is
deliberate. A pipeline describes exactly the attributes its vertex shader
reads; an attribute fed to a shader that ignores it is reported
(`WARNING-Shader-OutputNotConsumed`), and the stride already skips the bytes
nobody reads. So the attribute and the shader input that reads it arrive
together, in one step. The array `meshVertexAttributes()` returns, in
`GpuMesh.cpp`, gains its fourth entry:

```cpp
// GpuMesh.cpp, appended to the attribute array meshVertexAttributes() returns (Chapter 15).
{ .location = 3, .binding = 0, .format = VK_FORMAT_R32G32B32A32_SFLOAT,
  .offset = offsetof(pf::scene::Vertex, tangent) },
```

The vertex shader gains the matching input and one output, and one
subtlety. A tangent lies *in* the surface, so it transforms with the model
matrix itself, not with the normal matrix (which exists because normals do
not). And a transform that **mirrors** — a negative scale, which Chapter 14
uses to represent a mirrored USD prim — flips the handedness of the frame:
`cross(N, T)` then points the other way from the true bitangent, and the sign
in `w` must flip with it. Whether the model matrix's 3×3 part mirrors is the
sign of its **determinant** — Chapter 12 section 5's `dot(cross(x, y), z)`
mirror test, in one call: negative means mirrored.

```glsl
// Shaders/Scene/Mesh.vert.glsl - Chapter 15's three additions to Chapter 11's shader.

// 1. After the inUv input:
layout(location = 3) in vec4 inTangent;       // Chapter 15: meshVertexAttributes() location 3

// 2. After the uv output:
layout(location = 3) out vec4 worldTangent;   // xyz tangent, w bitangent sign

// 3. In main(), before gl_Position. A tangent lies in the surface: it transforms with the model
//    matrix, not the normal matrix. A mirroring transform reverses the frame's handedness, so the
//    sign flips too.
    mat3  linear = mat3(draw.model);
    float mirror = determinant(linear) < 0.0 ? -1.0 : 1.0;
    worldTangent = vec4(linear * inTangent.xyz, inTangent.w * mirror);
```

### `discard` needs a device feature

The cutout shader below is the tutorial's first with `discard`, and it brings a
device feature with it. `glslc --target-env=vulkan1.3` compiles GLSL's
`discard` to SPIR-V's `OpDemoteToHelperInvocation`, not the older `OpKill`, and
a shader module containing it fails validation
(`VUID-VkShaderModuleCreateInfo-pCode-08740`) unless
`shaderDemoteToHelperInvocation` is enabled. The demote form is the better
one: **a demoted pixel writes nothing, but keeps running as a helper for its
2×2 quad** (section 5), so its neighbours' derivatives — and their mip levels —
stay defined after the discard. The feature is required on every Vulkan 1.3
device, so nothing needs checking — only enabling, in `enable13`, where
designated initializers put it before `synchronization2`:

```cpp
// Chapter 02 section 6, CreateDevice - enable13 gains discard's feature (Chapter 15):
VkPhysicalDeviceVulkan13Features enable13{
    .sType                          = VK_STRUCTURE_TYPE_PHYSICAL_DEVICE_VULKAN_1_3_FEATURES,
    .shaderDemoteToHelperInvocation = VK_TRUE,   // GLSL discard (section 11)
    .synchronization2               = VK_TRUE,
    .dynamicRendering               = VK_TRUE,
};
```

Every later shader with a `discard` — Chapter 17's cutout shadow casters, the
grass — relies on this line rather than enabling it again.

### `materialOpacity`

The cutout test reads the material's opacity, and so does Chapter 17's
shadow-caster shader, which must cut out exactly the same pixels. So the test's
input is one function in `MaterialSet.glsl`, beside `remapScalar`:

```glsl
// MaterialSet.glsl (Chapter 15, section 11), after remapScalar: opacity, as the cutout test and
// Chapter 17's shadow casters read it.
float materialOpacity(vec2 uv)
{
    return material.opacity * remapScalar(texture(opacityTexture, uv), material.opacityMap);
}
```

### The fragment shader

The fragment shader is now the whole of sections 6 to 10 in order: evaluate
each input as `constant × remap(texel)`, build the shading normal from the
normal map, then light with section 9's `evaluatePreviewSurface`, by the model
`frame.brdf` names. Three things deserve a word before the code.

**Cutouts, and why they are a second pipeline.** `opacityThreshold` turns
opacity into a mask: below it, `discard` — the pixel is not drawn at all, not
even its depth. But a shader that *contains* `discard` costs every pixel it
draws, cut out or not: the GPU can no longer test and write depth before
running the fragment shader (early depth testing), because the shader might
still throw the pixel away. So the discard is behind a **specialization
constant** (Chapter 08 section 4's mechanism), `constant_id = 1`, and each
material is drawn with the pipeline built for it — the opaque one, whose
discard compiles out, or the cutout one. `constant_id = 0` stays Chapter 11's
`ShadingMode`. Chapter 18 adds a third, for alpha-to-coverage.

**The normal map, in the tangent frame.** Interpolation across a triangle
shortens the normal and tangent and bends them away from perpendicular, so
both are re-normalized and the tangent re-orthogonalized (Gram–Schmidt again,
per pixel). The bitangent is rebuilt from them and the sign. The normal map's
remapped value is then a direction *in that frame*. A back face's shading
normal is the front's, negated — the whole normal-mapped normal, so a bump on
the front of a leaf is a dent on its back, as it would be.

**The last debug view.** `ShadingMode::LitWithoutNormalMaps` lights the
geometry's own normal, for the side-by-side the exit check asks for.

The top of the file grows by one input, one constant, and the fourth view's
value (section 9 already added the `PreviewSurface.glsl` include):

```glsl
// Shaders/Scene/Mesh.frag.glsl (Chapter 15, Part 2). After the uv input:
layout(location = 3) in vec4 worldTangent;

// After constant_id 0:
layout(constant_id = 1) const bool alphaCutout = false; // the material's pipeline (section 11)

// After SHADING_MIP_LEVEL:
const uint SHADING_LIT_WITHOUT_NORMAL_MAPS = 3u;
```

and `main()` is replaced. Against section 9's version, three things are new:
the cutout test at the top, the tangent frame and the normal map in the middle,
and the view without normal maps:

```glsl
// Mesh.frag.glsl, main() (Chapter 15, Part 2): UsdPreviewSurface materials, still lit by Chapter 11's sun.
void main()
{
    // Cut out first: nothing below matters for a discarded pixel.
    float opacity = materialOpacity(uv);
    if (alphaCutout && opacity < material.opacityThreshold) { discard; }

    // Every input: constant * remap(texel) (section 6).
    SurfaceSample s;
    s.baseColor = material.baseColor.rgb * remap(texture(baseColorTexture, uv), material.baseColorMap).rgb;
    s.metallic  = material.metallic  * remapScalar(texture(metallicTexture,  uv), material.metallicMap);
    s.roughness = material.roughness * remapScalar(texture(roughnessTexture, uv), material.roughnessMap);
    s.ior       = material.ior;
    s.brdf      = frame.brdf;   // section 9's choice, the same for every pixel
    float occlusion = material.occlusion * remapScalar(texture(occlusionTexture, uv), material.occlusionMap);
    vec3  emissive  = material.emissiveColor.rgb * remap(texture(emissiveTexture, uv), material.emissiveMap).rgb;

    // The tangent frame, made orthonormal again after interpolation.
    vec3 N = normalize(worldNormal);
    vec3 T = normalize(worldTangent.xyz - N * dot(N, worldTangent.xyz));
    vec3 B = cross(N, T) * worldTangent.w;
    vec3 tangentNormal = remap(texture(normalTexture, uv), material.normalMap).xyz;
    if (shadingMode != SHADING_LIT_WITHOUT_NORMAL_MAPS)
    {
        N = normalize(T * tangentNormal.x + B * tangentNormal.y + N * tangentNormal.z);
    }
    if (!gl_FrontFacing) { N = -N; }   // double-sided meshes light their back (Chapter 11)

    // One sun, as in Chapter 11. sunColor is irradiance / pi (section 9).
    vec3 V = normalize(frame.cameraPosition.xyz - worldPosition);
    vec3 L = -frame.sunDirection.xyz;
    vec3 color = evaluatePreviewSurface(s, N, V, L, PI * frame.sunColor.rgb)
               + evaluateAmbient(s, frame.ambientColor.rgb, occlusion)
               + emissive;

    // The normals view: decoded here, so that after the composite's encode the screen shows n * 0.5 + 0.5.
    if (shadingMode == SHADING_NORMALS)   { color = srgbToLinear(N * 0.5 + 0.5); }
    if (shadingMode == SHADING_MIP_LEVEL) { color = mipLevelColor(textureQueryLod(baseColorTexture, uv).x); }

    // Half float holds 65504 at most; past it is infinity, and the composite would make NaN.
    outColor = vec4(min(color, vec3(64000.0)), 1.0);
}
```

Every `if` on `shadingMode` or `alphaCutout` tests a specialization constant, so
each pipeline's compiled shader contains only its own branch. The test on
`s.brdf` inside `evaluatePreviewSurface` is the other kind: decided at run time,
but uniform (section 9).

### The pipelines

Chapter 11's `CreatePipelines` builds one mesh pipeline per `ShadingMode`, with
a one-entry specialization for `constant_id = 0`. It now builds two per mode,
with a two-entry specialization, and `ShadingMode` gains its fourth value,
`LitWithoutNormalMaps = 3`, so `SHADING_MODE_COUNT` becomes 4:

```cpp
    // In CreatePipelines (Chapter 15), replacing Chapter 11's loop: the two constants the mesh
    // fragment shader declares, and a pipeline for every pair of values.
    struct MeshSpecialization
    {
        uint32_t shadingMode = 0;          // constant_id 0
        VkBool32 alphaCutout = VK_FALSE;   // constant_id 1 - a GLSL bool is a 4-byte VkBool32
    };
    const VkSpecializationMapEntry meshEntries[] = {
        { .constantID = 0, .offset = offsetof(MeshSpecialization, shadingMode), .size = sizeof(uint32_t) },
        { .constantID = 1, .offset = offsetof(MeshSpecialization, alphaCutout), .size = sizeof(VkBool32) },
    };

    for (uint32_t mode = 0; mode < SHADING_MODE_COUNT; ++mode)
    {
        for (uint32_t cutout = 0; cutout < 2; ++cutout)
        {
            const MeshSpecialization values{ .shadingMode = mode, .alphaCutout = cutout ? VK_TRUE : VK_FALSE };
            const VkSpecializationInfo specialization{
                .mapEntryCount = 2,
                .pMapEntries   = meshEntries,
                .dataSize      = sizeof(values),
                .pData         = &values,
            };
            // Chapter 11's description, unchanged: only the specialization differs per pipeline.
            const GraphicsPipelineDesc desc{
                .vertexShader           = "Scene/Mesh.vert.spv",
                .fragmentShader         = "Scene/Mesh.frag.spv",
                .vertexBindings         = meshVertexBindings(),
                .vertexAttributes       = meshVertexAttributes(),
                .colorFormats           = { &m_formats.color, 1 },
                .depthFormat            = m_formats.depth,
                .depthTest              = true,
                .depthWrite             = true,
                .depthCompare           = VK_COMPARE_OP_LESS,
                .cullMode               = VK_CULL_MODE_BACK_BIT,          // overridden per draw (dynamic)
                .frontFace              = VK_FRONT_FACE_COUNTER_CLOCKWISE, // overridden per frame (dynamic)
                .dynamicStates          = dynamicStates,
                .fragmentSpecialization = &specialization,
                .layout                 = m_meshLayout,
            };
            m_meshPipelines[mode][cutout] = createGraphicsPipeline(m_context.device, m_pipelineCache, desc);
            if (m_meshPipelines[mode][cutout] == VK_NULL_HANDLE)
            {
                return InitializationResult::failure("Creating a mesh pipeline failed.");
            }
        }
    }
```

Eight pipelines from one pair of shaders. `DestroyPipelines` destroys all
eight — its loop gains the inner dimension:

```cpp
// DestroyPipelines (Chapter 15): m_meshPipelines is two-dimensional now.
    for (std::array<VkPipeline, 2>& pipelines : m_meshPipelines)
    {
        for (VkPipeline& pipeline : pipelines)
        {
            vkDestroyPipeline(m_context.device, pipeline, nullptr);
            pipeline = VK_NULL_HANDLE;
        }
    }
```

**`RecordDraws` picks between them per material.** Chapter 11 bound the
pipeline once, at the top of the function. That line goes; a `boundPipeline`
joins section 7's `boundMaterial` before the loop:

```cpp
    VkPipeline boundPipeline = VK_NULL_HANDLE;   // RecordDraws (Chapter 15, section 11), beside boundMaterial
```

and section 7's material branch binds the material's pipeline before its set:

```cpp
        // RecordDraws: section 7's material branch, grown. Per material change: its pipeline, opaque
        // or cutout, and its set 1.
        if (item.material != boundMaterial)
        {
            const GpuMaterial& material = m_gpuMaterials[item.material];
            const VkPipeline   pipeline = m_meshPipelines[static_cast<uint32_t>(m_shading)][material.cutout ? 1 : 0];
            if (pipeline != boundPipeline)
            {
                vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, pipeline);
                boundPipeline = pipeline;
            }
            vkCmdBindDescriptorSets(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, m_meshLayout,
                                    1, 1, &material.set, 0, nullptr);   // firstSet = 1
            boundMaterial = item.material;
        }
```

Set 0 is still bound once per list, now before any pipeline is, which is fine:
a descriptor set is bound against a pipeline *layout*, not a pipeline, and it
stays bound across pipeline changes as long as the layouts agree up to that set
number. Every mesh pipeline shares `m_meshLayout`, so set 0 is bound once per
list and set 1 once per material change.

The viewer gets the last debug view's button:

```cpp
// Demos/UsdViewer/UsdViewerDemo.cpp, DrawPanel: after section 8's "Mip level" radio button
// (Chapter 15).
ImGui::SameLine();
ImGui::RadioButton("Without normal maps", &shading, 3);
```

---

## 12. Transparency, and why it is not here

A material with `opacity` below 1 and no `opacityThreshold` is *transparent*:
glass, a soap bubble, a tinted window. This chapter draws it opaque and says so
in the log. The reason is not that blending is hard to switch on — Chapter 06's
`BlendMode::Alpha` already exists — but that correct transparency is a
different *kind* of rendering:

- A transparent surface does not hide what is behind it, so it must not write
  depth, and everything behind it must already be drawn. Transparent surfaces
  are drawn **after** every opaque one, in a separate pass.
- Blending is order-dependent: two overlapping glass panes give a different
  color depending on which is drawn first. Correct results need the
  transparent draws **sorted back to front**, every frame, and even sorting
  fails for surfaces that interpenetrate.
- A transparent surface still reflects (Fresnel), so it needs the lit color
  *and* a coverage value — which is what `opacityMode` chooses between.

The clean answers — sorting with a separate pass, or order-independent
transparency (weighted blended, or per-pixel linked lists) — each deserve a
chapter. **Cutouts** cover what scenes mostly need from opacity — foliage,
fences, grilles, decals with holes — with none of that machinery, because a
cut-out pixel is either fully there or fully gone. Their edges stair-step at
the texel boundary of the mask; Chapter 18's **alpha-to-coverage** smooths them
with MSAA's samples.

---

## 13. The test scenes

Part 1's `MaterialTest.usda` has two more objects, which Part 2 makes work:

| Object | Tests | What to see |
| --- | --- | --- |
| `BumpsPanel` | Normal map, tangents | Sixteen round bumps, each lit on the side facing the sun |
| `LeafPanel` | Cutout, `doubleSided` | A green ellipse with the quad around it cut away, visible from behind |

**`MaterialSweep.usda`**, section 9's checkpoint scene, is two rows of five
spheres, roughness 0, 0.25, 0.5, 0.75, and 1 from left to right: grey plastic
in front, gold behind. Ten materials that differ in two numbers are tedious to
type and easy to get wrong, so Appendix B's script writes the file along with
the textures. The spheres are USD `Sphere` prims, which Chapter 14 turns into
Chapter 11's `makeUvSphere` — which now ends in `generateTangents`, so after
section 11 they look exactly as they did at section 9's checkpoint.

**A Blender scene** is the third test, and the one ROADMAP step 16's exit check
names. Any model with Principled BSDF materials and image textures will do — a
CC0 material from ambientCG or Poly Haven on a sphere and a cube is plenty.
Export with **File → Export → Universal Scene Description**, *Materials* and
*Textures* ticked. Blender writes a UsdPreviewSurface network per material,
copies the images into a `textures/` folder beside the `.usda`, and always
writes wrap modes, `sourceColorSpace`, and the normal map's scale and bias.
Two things it writes that this chapter reports rather than draws. First,
`opacity` without `opacityThreshold` for any material whose Alpha is connected
— drawn opaque, with section 4's warning. Blender 4.2 removed the *Alpha Clip*
blend mode, and 4.5's exporter writes a threshold only when it finds one in the
node tree: put a **Math node set to Round** between the image's Alpha and the
Principled BSDF's Alpha, and it writes `opacityThreshold = 0.5`. (A *Less Than*
followed by *1 − x* also works, with the Less Than's threshold; that pair is
what Blender converts an older file's Alpha Clip into.) Second, an
`emissiveColor` that is color × strength, so above 1 for any strength above 1 —
clipped to white until Chapter 16's tone curve.

---

## Exit check

Run `UsdViewerDemo` with validation on. Part 1's checkpoint still holds, in
every view and under every BRDF, and so does section 9's on
`MaterialSweep.usda`; the rest of Part 2 adds:

- [ ] **The normal map changes the lighting.** In `Lit`, `BumpsPanel` shows
      sixteen bumps, each bright on the side toward the sun and dark on the
      other; in "Without normal maps" it is a flat grey panel. Move the sun
      (the viewer's sun sliders): the bright sides follow it. If the bumps look
      lit from *below* while the sun is above, the bitangent sign is wrong —
      section 10's negated v.
- [ ] **Cutouts.** `LeafPanel` is a green ellipse with clean (if stair-stepped)
      edges, nothing drawn around it, and visible from behind.
- [ ] **A Blender scene** with image textures matches Blender's Material
      Preview in what does not depend on lighting: the same images on the same
      faces, metals that look metallic (dark where they reflect nothing, with
      tinted highlights), and normal-map bumps that show in "Lit" and are gone
      in "Without normal maps". (For a closer comparison, light Blender's
      viewport with a single sun and no world.)
- [ ] Synchronization validation, proven on by Chapter 05's positive control and
      by Part 1's mip-chain control, stays silent while loading and drawing.

Next: [16 — Lights](16-Lights.md)

---

## Sources

- Pixar, *UsdPreviewSurface Specification*: the inputs of section 1,
  `UsdUVTexture`, the `auto` color-space rule, and roughness squared before use.
- J. F. Blinn, "Models of Light Reflection for Computer Synthesized Pictures",
  SIGGRAPH 1977: the half-vector highlight of section 9 (b).
- T. S. Trowbridge and K. P. Reitz, "Average Irregularity Representation of a
  Rough Surface for Ray Reflection", JOSA 1975; B. Walter, S. Marschner, H. Li,
  and K. Torrance, "Microfacet Models for Refraction through Rough Surfaces",
  EGSR 2007, which named it GGX: section 9 (c)'s D.
- B. Smith, "Geometrical Shadowing of a Random Rough Surface", IEEE
  Transactions on Antennas and Propagation, 1967: G. C. Schlick, "An
  Inexpensive BRDF Model for Physically-based Rendering", Eurographics 1994:
  the Fresnel approximation, and the approximation of G used here.
- B. Karis, "Real Shading in Unreal Engine 4", SIGGRAPH 2013 course notes: the
  metallic workflow and the microfacet model as real-time renderers ship them.
- M. Mikkelsen, "Simulation of Wrinkled Surfaces Revisited", 2008: MikkTSpace
  (section 10).

---

## Appendix A — `MaterialTest.usda`

Reference, to copy: the test scene of sections 8 and 13, written by hand. Each
panel is a quad in the XY plane facing +Z, standing on the floor.

```usda
#usda 1.0
(
    defaultPrim = "MaterialTest"
    metersPerUnit = 1
    upAxis = "Y"
)

def Xform "MaterialTest"
{
    def Scope "Materials"
    {
        # Diffuse color from a tiled texture: the mipmap test.
        def Material "Checker"
        {
            token outputs:surface.connect = </MaterialTest/Materials/Checker/Surface.outputs:surface>

            def Shader "Surface"
            {
                uniform token info:id = "UsdPreviewSurface"
                color3f inputs:diffuseColor.connect = </MaterialTest/Materials/Checker/Albedo.outputs:rgb>
                float inputs:roughness = 0.9
                token outputs:surface
            }

            def Shader "Albedo"
            {
                uniform token info:id = "UsdUVTexture"
                asset inputs:file = @Textures/Checker.png@
                token inputs:sourceColorSpace = "sRGB"
                token inputs:wrapS = "repeat"
                token inputs:wrapT = "repeat"
                float2 inputs:st.connect = </MaterialTest/Materials/Checker/TexCoord.outputs:result>
                float3 outputs:rgb
            }

            def Shader "TexCoord"
            {
                uniform token info:id = "UsdPrimvarReader_float2"
                string inputs:varname = "st"
                float2 outputs:result
            }
        }

        # Emission only, from an 8-bit RGBA texture marked "auto": the color check. A black metal
        # reflects nothing at all, so what reaches the screen is exactly the texture.
        def Material "GreyBands"
        {
            token outputs:surface.connect = </MaterialTest/Materials/GreyBands/Surface.outputs:surface>

            def Shader "Surface"
            {
                uniform token info:id = "UsdPreviewSurface"
                color3f inputs:diffuseColor = (0, 0, 0)
                float inputs:metallic = 1
                color3f inputs:emissiveColor.connect = </MaterialTest/Materials/GreyBands/Bands.outputs:rgb>
                token outputs:surface
            }

            def Shader "Bands"
            {
                uniform token info:id = "UsdUVTexture"
                asset inputs:file = @Textures/GreyBands.png@
                token inputs:sourceColorSpace = "auto"
                token inputs:wrapS = "clamp"
                token inputs:wrapT = "clamp"
                float2 inputs:st.connect = </MaterialTest/Materials/GreyBands/TexCoord.outputs:result>
                float3 outputs:rgb
            }

            def Shader "TexCoord"
            {
                uniform token info:id = "UsdPrimvarReader_float2"
                string inputs:varname = "st"
                float2 outputs:result
            }
        }

        # A constant grey with a normal map: the tangent test.
        def Material "Bumps"
        {
            token outputs:surface.connect = </MaterialTest/Materials/Bumps/Surface.outputs:surface>

            def Shader "Surface"
            {
                uniform token info:id = "UsdPreviewSurface"
                color3f inputs:diffuseColor = (0.5, 0.5, 0.5)
                float inputs:roughness = 0.4
                normal3f inputs:normal.connect = </MaterialTest/Materials/Bumps/Normal.outputs:rgb>
                token outputs:surface
            }

            def Shader "Normal"
            {
                uniform token info:id = "UsdUVTexture"
                asset inputs:file = @Textures/Bumps.png@
                token inputs:sourceColorSpace = "raw"
                token inputs:wrapS = "repeat"
                token inputs:wrapT = "repeat"
                float4 inputs:scale = (2, 2, 2, 1)
                float4 inputs:bias = (-1, -1, -1, 0)
                float2 inputs:st.connect = </MaterialTest/Materials/Bumps/TexCoord.outputs:result>
                float3 outputs:rgb
            }

            def Shader "TexCoord"
            {
                uniform token info:id = "UsdPrimvarReader_float2"
                string inputs:varname = "st"
                float2 outputs:result
            }
        }

        # Color and alpha from one sRGB texture; alpha below 0.5 is cut away.
        def Material "Leaf"
        {
            token outputs:surface.connect = </MaterialTest/Materials/Leaf/Surface.outputs:surface>

            def Shader "Surface"
            {
                uniform token info:id = "UsdPreviewSurface"
                color3f inputs:diffuseColor.connect = </MaterialTest/Materials/Leaf/Image.outputs:rgb>
                float inputs:opacity.connect = </MaterialTest/Materials/Leaf/Image.outputs:a>
                float inputs:opacityThreshold = 0.5
                token outputs:surface
            }

            def Shader "Image"
            {
                uniform token info:id = "UsdUVTexture"
                asset inputs:file = @Textures/Leaf.png@
                token inputs:sourceColorSpace = "sRGB"
                token inputs:wrapS = "clamp"
                token inputs:wrapT = "clamp"
                float2 inputs:st.connect = </MaterialTest/Materials/Leaf/TexCoord.outputs:result>
                float3 outputs:rgb
                float outputs:a
            }

            def Shader "TexCoord"
            {
                uniform token info:id = "UsdPrimvarReader_float2"
                string inputs:varname = "st"
                float2 outputs:result
            }
        }

        # A texture that does not exist: the importer must say so and use the fallback.
        def Material "Missing"
        {
            token outputs:surface.connect = </MaterialTest/Materials/Missing/Surface.outputs:surface>

            def Shader "Surface"
            {
                uniform token info:id = "UsdPreviewSurface"
                color3f inputs:diffuseColor.connect = </MaterialTest/Materials/Missing/Image.outputs:rgb>
                token outputs:surface
            }

            def Shader "Image"
            {
                uniform token info:id = "UsdUVTexture"
                asset inputs:file = @Textures/DoesNotExist.png@
                float4 inputs:fallback = (1, 0, 1, 1)
                float2 inputs:st.connect = </MaterialTest/Materials/Missing/TexCoord.outputs:result>
                float3 outputs:rgb
            }

            def Shader "TexCoord"
            {
                uniform token info:id = "UsdPrimvarReader_float2"
                string inputs:varname = "st"
                float2 outputs:result
            }
        }
    }

    # The view the exit check describes: the panels ahead, the floor running away below them.
    def Camera "Camera"
    {
        float focalLength = 24
        float verticalAperture = 24
        float2 clippingRange = (0.1, 200)
        double3 xformOp:translate = (0, 2, 10)
        float xformOp:rotateX = -3
        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateX"]
    }

    # 40 x 40 m, the checker repeated 20 times each way.
    def Mesh "Floor" (
        prepend apiSchemas = ["MaterialBindingAPI"]
    )
    {
        int[] faceVertexCounts = [4]
        int[] faceVertexIndices = [0, 1, 2, 3]
        point3f[] points = [(-20, 0, 20), (20, 0, 20), (20, 0, -20), (-20, 0, -20)]
        texCoord2f[] primvars:st = [(0, 0), (20, 0), (20, 20), (0, 20)] (
            interpolation = "vertex"
        )
        uniform token subdivisionScheme = "none"
        rel material:binding = </MaterialTest/Materials/Checker>
    }

    # Each panel below is a quad in the XY plane facing +Z, standing on the floor.
    def Mesh "GreyBandsPanel" (
        prepend apiSchemas = ["MaterialBindingAPI"]
    )
    {
        int[] faceVertexCounts = [4]
        int[] faceVertexIndices = [0, 1, 2, 3]
        point3f[] points = [(-4, 2.5, 0), (4, 2.5, 0), (4, 3.5, 0), (-4, 3.5, 0)]
        texCoord2f[] primvars:st = [(0, 0), (1, 0), (1, 1), (0, 1)] (
            interpolation = "vertex"
        )
        uniform token subdivisionScheme = "none"
        rel material:binding = </MaterialTest/Materials/GreyBands>
    }

    def Mesh "BumpsPanel" (
        prepend apiSchemas = ["MaterialBindingAPI"]
    )
    {
        int[] faceVertexCounts = [4]
        int[] faceVertexIndices = [0, 1, 2, 3]
        point3f[] points = [(-4, 0.25, 0), (-1.75, 0.25, 0), (-1.75, 2.25, 0), (-4, 2.25, 0)]
        texCoord2f[] primvars:st = [(0, 0), (1, 0), (1, 1), (0, 1)] (
            interpolation = "vertex"
        )
        uniform token subdivisionScheme = "none"
        rel material:binding = </MaterialTest/Materials/Bumps>
    }

    def Mesh "LeafPanel" (
        prepend apiSchemas = ["MaterialBindingAPI"]
    )
    {
        uniform bool doubleSided = 1
        int[] faceVertexCounts = [4]
        int[] faceVertexIndices = [0, 1, 2, 3]
        point3f[] points = [(-1.5, 0.25, 0), (2.5, 0.25, 0), (2.5, 2.25, 0), (-1.5, 2.25, 0)]
        texCoord2f[] primvars:st = [(0, 0), (1, 0), (1, 1), (0, 1)] (
            interpolation = "vertex"
        )
        uniform token subdivisionScheme = "none"
        rel material:binding = </MaterialTest/Materials/Leaf>
    }

    def Mesh "MissingPanel" (
        prepend apiSchemas = ["MaterialBindingAPI"]
    )
    {
        int[] faceVertexCounts = [4]
        int[] faceVertexIndices = [0, 1, 2, 3]
        point3f[] points = [(2.75, 0.25, 0), (4, 0.25, 0), (4, 2.25, 0), (2.75, 2.25, 0)]
        texCoord2f[] primvars:st = [(0, 0), (1, 0), (1, 1), (0, 1)] (
            interpolation = "vertex"
        )
        uniform token subdivisionScheme = "none"
        rel material:binding = </MaterialTest/Materials/Missing>
    }
}
```

## Appendix B — `make_test_assets.py`

Reference, to copy: writes the four textures `MaterialTest.usda` uses, and
`MaterialSweep.usda`. Plain Python 3 runs it; so does the Python inside Blender
(`blender --background --python make_test_assets.py`).

```python
# Assets/Scenes/make_test_assets.py
# Writes the four textures MaterialTest.usda uses, and MaterialSweep.usda. Run once,
# from Assets/Scenes/:
#     python make_test_assets.py
# Plain Python 3, standard library only. Not part of the build: what it writes is
# committed like any other asset.
import math, os, struct, zlib

os.makedirs("Textures", exist_ok=True)

def write_png(name, width, height, pixel):          # pixel(x, y) -> (r, g, b, a), 0-255
    rows = b"".join(b"\x00" + bytes(c for x in range(width) for c in pixel(x, y))
                    for y in range(height))          # row 0 is the TOP of the image
    def chunk(kind, data):
        return (struct.pack(">I", len(data)) + kind + data +
                struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)   # 8-bit RGBA
    with open(name, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) +
                chunk(b"IDAT", zlib.compress(rows, 9)) + chunk(b"IEND", b""))

# Eight grey bands whose sRGB byte values you can read back off the screen.
BANDS = [0, 32, 64, 96, 128, 160, 188, 255]
write_png("Textures/GreyBands.png", 256, 32, lambda x, y: (BANDS[x // 32],) * 3 + (255,))

# A checkerboard: 8 x 8 squares, two greys. Tiled across the floor, it is what
# mipmaps exist for.
def checker(x, y):
    v = 200 if ((x // 32) + (y // 32)) % 2 == 0 else 60
    return (v, v, v, 255)
write_png("Textures/Checker.png", 256, 256, checker)

# A normal map: a 4 x 4 grid of round bumps. OpenGL convention, like Blender's:
# +X right, +Y UP the image, +Z out of the surface; stored as n * 0.5 + 0.5.
def bumps(x, y):
    u = (x % 64 - 31.5) / 28.0
    v = -(y % 64 - 31.5) / 28.0                      # image rows run down; +Y is up
    r2 = u * u + v * v
    nx, ny, nz = (u, v, math.sqrt(1.0 - r2)) if r2 < 1.0 else (0.0, 0.0, 1.0)
    return (round((nx * 0.5 + 0.5) * 255), round((ny * 0.5 + 0.5) * 255),
            round((nz * 0.5 + 0.5) * 255), 255)
write_png("Textures/Bumps.png", 256, 256, bumps)

# A leaf: green, with alpha 255 inside an ellipse and 0 outside.
def leaf(x, y):
    u, v = (x - 127.5) / 120.0, (y - 127.5) / 60.0
    inside = u * u + v * v < 1.0
    return (60, 140, 40, 255 if inside else 0)
write_png("Textures/Leaf.png", 256, 256, leaf)

# Two rows of spheres, roughness 0 to 1 left to right: plastic in front, gold behind, and a
# camera that frames them.
# Ten materials that differ in two numbers - too repetitive to type by hand.
ROUGHNESS = [0.0, 0.25, 0.5, 0.75, 1.0]
ROWS = [("Plastic", (0.6, 0.6, 0.6), 0.0, 0.0), ("Gold", (1.0, 0.77, 0.34), 1.0, -1.25)]
materials, spheres = [], []
for row, color, metallic, z in ROWS:
    for i, roughness in enumerate(ROUGHNESS):
        name = f"{row}{i}"
        materials.append(f"""
        def Material "{name}"
        {{
            token outputs:surface.connect = </MaterialSweep/Materials/{name}/Surface.outputs:surface>

            def Shader "Surface"
            {{
                uniform token info:id = "UsdPreviewSurface"
                color3f inputs:diffuseColor = {color}
                float inputs:metallic = {metallic}
                float inputs:roughness = {roughness}
                token outputs:surface
            }}
        }}""")
        spheres.append(f"""
    def Sphere "{name}Sphere" (
        prepend apiSchemas = ["MaterialBindingAPI"]
    )
    {{
        double radius = 0.4
        double3 xformOp:translate = ({(i - 2) * 1.0}, 0.5, {z})
        uniform token[] xformOpOrder = ["xformOp:translate"]
        rel material:binding = </MaterialSweep/Materials/{name}>
    }}""")

with open("MaterialSweep.usda", "w") as f:
    f.write("#usda 1.0\n(\n    defaultPrim = \"MaterialSweep\"\n    metersPerUnit = 1\n    upAxis = \"Y\"\n)\n\n")
    f.write("def Xform \"MaterialSweep\"\n{\n    def Scope \"Materials\"\n    {")
    f.write("".join(materials))
    f.write("\n    }\n")
    f.write("".join(spheres))
    f.write("""

    def Camera "Camera"
    {
        float focalLength = 24
        float verticalAperture = 24
        float2 clippingRange = (0.1, 100)
        double3 xformOp:translate = (0, 2, 6.5)
        float xformOp:rotateX = -12
        uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:rotateX"]
    }""")
    f.write("\n}\n")
```
