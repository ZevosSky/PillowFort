# 38 — Ground Materials

**Goal:** ground that is made of something. The erosion script that made the
island also writes a **material map**: six weights for every 32 m of it, sand
by the sea, grass on gentle ground, soil along the main streams, scree where
the water dropped its load under the cliffs, rock on the steep, and snow on the
high gentle tops. From afar the terrain is painted by that map, in lighter and
darker patches so that no meadow is one flat green; up close it shows six CC0
photographs of ground, tinted to the island's colours, laid at their real size,
meeting where the higher one stands proud of the other, with their normals in
the light, the rock wrapped round the cliffs from three sides, and all of it
fading into the far colours between 150 and 300 m. Debug views show the weights
and count what each pixel costs.

**ROADMAP:** step 21+ — the `Horizon` demo grows. A class of its own,
`GroundMaterials`, in `Source/PillowFort/Demos/Horizon/`, owned by `Terrain`;
a shader include, `Shaders/Horizon/GroundMaterials.glsl`; the map, written by
`Assets/Terrain/make_island.py` (the appendix) beside the heightmap in
`Assets/Terrain/Island/`; the six photographs in `Assets/Terrain/Ground/`. All
three are on the `start` branch.

**Module:** `pf::demos::horizon` (`GroundMaterials`, owned by `Terrain`;
`Terrain` and `HorizonDemo` grow). One function goes outside the demo,
`usd_import::ImportRgbaImage8`, beside Chapter 36's `ImportGrayImage16`, for
the same reason: the importer is the only code that includes a TinyUSDZ header.

**Math:** taught where it is first used, and listed in the index's [The math,
chapter by chapter](../VulkanTutorial.md#the-math-chapter-by-chapter): weights
that add up to 1 (section 1); an octave faded by the ground a pixel covers
(section 3); a texel's size against a pixel's, and a gain in linear light
(section 6); a tangent from a world axis (section 7); blending by height
(section 8); three projections weighted by the normal (section 9). It reuses
Chapter 16 section 5's `smoothstep`, Chapter 15 section 10's Gram-Schmidt,
Chapter 10's rotation and cross product, and Chapter 08 section 4's sRGB curve.

**Prerequisites:**

- Builds on Chapters 36 and 37, built and running. From 36: the octave fade rule,
  full strength while a wavelength spans four cells and gone by two (section 3);
  the normal from central differences, and `up` (section 4); the erosion script,
  its droplets and its work grid of 32 m cells, and why another Python makes
  another island (section 7); `ImportGrayImage16`, `transitionLevels` and the
  upload's three barriers (section 8); set 1, `mapHeight`'s uv, `MAP_ORIGIN` and
  the CPU's `MapHeight` (section 9); the sea and its floor seen through shallow
  water (section 10); the haze, with the debug views drawn after it (section 11).
  From 37, the chapter just read: `HorizonShading.glsl`'s `lightAt`, the views
  and `GoTo`, `valueNoise` and **Show forest**, `sunShadow` and the two-argument
  `lightAt(N, sunLit)`, and the **Times** header, each named again where this
  chapter uses it.
- Chapter 15 sections 4 (sRGB or raw, and a flat normal decoded as sRGB, which
  leans 39 degrees), 5 (a mip chain made by blits, the material sampler, and
  "How the sampler picks a level: 2×2 quads and derivatives") and 10 (tangents,
  Gram-Schmidt, and green up the image); Chapter 17 sections 3 (one image of
  several layers, and a view of all of them for sampling) and 6 (an array image
  sampled with the layer as one more coordinate); Chapter 16 section 5
  (`smoothstep`); Chapter 30 section 10 (the sun's lobe on the water, in
  `waterColor`).
- Chapter 10 sections 1 (a matrix times a vector), 4 (the 60-degree lens) and 8
  (the box "Normals and the cross product"); Chapter 08 sections 2 (a staging
  buffer and `immediateSubmit`) and 4 (an `_SRGB` image is decoded when it is
  sampled); Chapter 04 section 5 (the three questions a barrier answers);
  Chapter 02 section 2 (validation, with the synchronization validation and the
  shader-access setting it requests).
- Chapter 09 section 6 (`beginDemoPanel`, whose height stops at the screen's
  edge); Chapter 13 section 6 (`Assets/` beside the executable).

---

## Where this is going

Chapter 37 stood things on the island. The ground under them is still what
Chapter 36 made it: four flat colours chosen by height and slope, sand by the
sea, grass, rock where the vertex normal is steep, snow over 820 m. From the
viewpoint that reads well enough. Fly down to the wood or the shore and it
falls apart: the grass is one flat green to the horizon, the beach one flat
tan, and the rock appears only where a whole ring cell is steep, so it slides
about as the rings move.

This chapter gives the ground its materials, in three parts:

- **Part 1, "What the ground is made of"** (sections 1-4): the erosion script
  records where its raindrops ran and writes six weights per 32 m cell into two
  small images; the GPU gets them as one image of two layers, in the set that
  becomes the island's; the terrain shader paints the ground by them; and a
  readout under the camera and five places to look from check it. It ends with
  the island painted by its map, and no file downloaded.
- **Part 2, "Up close"** (sections 5-8): six photographs of ground, each with a
  colour, a normal map and a height map, laid at their real size, tinted at load
  to the island's colours, lit through their normals, and meeting by height, so
  that borders are clumps and stones, not a cross-fade 32 m wide.
- **Part 3, "Cliffs and distance"** (sections 9-11): rock projected from three
  sides, so cliffs do not smear; the photographs fading into the far colours
  between 150 and 300 m; and what all of it costs, counted per pixel, with a
  budget and what to cut first.

One fact shapes the chapter: **what the ground is made of is decided once,
offline, where the water went.** A shader can tell slope and height per pixel,
but not where water ran for centuries; the erosion script knows, because it ran
it. So the script writes the map, and the shader reads it, adding only what the
map is too coarse to see: rock on a ledge narrower than a cell.

> **Jump:** the terrain's fragment shader has been short: one light, one
> albedo, haze. It grows here by a few hundred lines of material code in an
> include, and from section 6 most of what it reads sits inside branches. Keep
> in mind the shape the chapter holds to: the map's two reads at the top
> (section 2), the far colour always (section 3), and the photographs only where
> they show (sections 6 to 10).

### What you are actually writing

Every pixel of the terrain, in `Terrain.frag.glsl`'s `main`, with the section
that writes each part:

```text
 the map's six weights here                                            section 2
 the ground's derivatives across a pixel, and the ground it covers     sections 3, 6
 under water: the floor, from the map; up close, the sand's photograph  sections 3, 6
 on land: rock where this pixel is steep; the colour from afar, varied  section 3
   near: each photograph read, rock from three sides                   sections 6, 9
         shares by height; the normals                                 sections 8, 7
         fading into the far colour from 150 m to 300 m                section 10
 lit, shadowed, hazed (Chapters 36, 37)
 the views: false colours, the reads it made                           sections 2, 11
```

**This is `GroundMaterials.h`**, the map of the chapter. The materials are a
class of their own, owned by the terrain, which puts their images in its set.
The images are made once, in `Setup`, as the heightmap's are. Every function
names the section that writes it:

```cpp
///========================================================
/// @author Gary Yang
/// @brief  Chapter 38: what the ground is made of: the island's material map, and six photographs of it
/// @copyright (C) Gary 2026
///========================================================

// Source/PillowFort/Demos/Horizon/GroundMaterials.h
#pragma once

#include "PillowFort/ErrorReporting/InitializationResult.h"
#include "PillowFort/VulkanGraphics/VulkanResources.h"

#include <glm/glm.hpp>
#include <vulkan/vulkan.h>
#include <vma/vk_mem_alloc.h>

#include <array>
#include <cstdint>
#include <vector>

namespace pf::demos::horizon {

// Section 1: the six materials, in the order the map stores their weights: weight i is in layer i / 3 of the
// map, channel i % 3. Section 5: the photographs' layers use the same order.
inline constexpr uint32_t GROUND_LAYERS = 6;
inline constexpr std::array<const char*, GROUND_LAYERS> GROUND_NAMES{ "Sand", "Grass", "Soil", "Scree", "Rock", "Snow" };

// Section 2: who reads the island's images (set 1, Terrain): whatever draws or computes over the island, so
// every binding is visible to these stages, and every upload's last barrier waits for them.
inline constexpr VkShaderStageFlags ISLAND_STAGES =
    VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT | VK_SHADER_STAGE_COMPUTE_BIT;
inline constexpr VkPipelineStageFlags2 ISLAND_READERS =
    VK_PIPELINE_STAGE_2_VERTEX_SHADER_BIT | VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT | VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT;

// Section 2: an image of one or more layers with every mip level, and the view the shaders read it through.
struct LayeredImage
{
    VkImage       image      = VK_NULL_HANDLE;
    VmaAllocation allocation = VK_NULL_HANDLE;
    VkImageView   view       = VK_NULL_HANDLE;
};

// The island's materials. The terrain owns one, and puts its images in the island's set.
class GroundMaterials
{
public:
    // Section 2: the material map, from its two files to a two-layer image. Section 5: the six photographs,
    // prepared and uploaded as two six-layer images. Missing files are reported, not fatal: one-texel
    // stand-ins keep the set valid, and the terrain draws without them. `mapMetres` is the side of the square
    // the map covers, the heightmap's.
    InitializationResult Initialize(const vulkan_graphics::VulkanContext& context, float mapMetres);
    void                 Shutdown();   // the host has idled the device; safe after a partial Initialize

    // Section 2: the map's side in texels, 0 when it could not be loaded. Section 5: the photographs'.
    uint32_t MapSize() const { return m_hasMap ? m_mapSize : 0; }
    uint32_t TextureSize() const { return m_hasTextures ? m_textureSize : 0; }

    // Section 4: groundWeights on the CPU: the six weights at xz, as the GPU filters level 0, adding up to 1.
    std::array<float, GROUND_LAYERS> WeightsAt(glm::vec2 xz) const;

    // Section 2: what the island's set points at. Section 5: the photographs and their sampler.
    VkImageView MapView() const { return m_map.view; }
    VkImageView ColorView() const { return m_colors.view; }
    VkImageView NormalView() const { return m_normals.view; }
    VkSampler   LayerSampler() const { return m_layerSampler; }

private:
    void LoadMap();        // section 2
    void LoadTextures();   // section 5

    vulkan_graphics::VulkanContext m_context;   // copies of borrowed handles
    float                          m_mapMetres = 0.0f;

    // Section 2: the map. Level 0 of both layers stays on the CPU for WeightsAt, four bytes a texel.
    std::vector<uint8_t> m_mapTexels;
    uint32_t             m_mapSize = 0;       // texels per side
    bool                 m_hasMap  = false;   // false: a one-texel stand-in, and Chapter 37's ground
    LayeredImage         m_map;

    // Section 5: the photographs, one layer each: colour, with the height in alpha (section 8), and normals.
    std::vector<uint8_t> m_colorTexels;
    std::vector<uint8_t> m_normalTexels;
    uint32_t             m_textureSize = 0;
    bool                 m_hasTextures = false;   // false: one-texel stand-ins, and the far colours up close too
    LayeredImage         m_colors;
    LayeredImage         m_normals;
    VkSampler            m_layerSampler = VK_NULL_HANDLE;
};

} // namespace pf::demos::horizon
```

`LayeredImage` is one image on the GPU with its view; the map is one, and the
photographs two more. `ISLAND_STAGES` and `ISLAND_READERS` are the same three
stages twice, once as the shader stages a descriptor binding is visible to and
once as the pipeline stages a barrier waits for; section 2 says why both are
all three. Write the whole header now: a declared function that is never
called needs no body, so the program builds at every step, and each section
fills in what it names. `LoadTextures` and the photographs' members wait for
section 5, `WeightsAt` for section 4.

`Terrain.h` gains the materials. Its include goes first, beside the others:

```cpp
#include "PillowFort/Demos/Horizon/GroundMaterials.h"
```

The member goes after the heightmap's members and above the set's three
handles. Members are destroyed in the reverse order of their declaration, so
the materials outlive the set that will point at their images (section 2):

```cpp
    // Chapter 38 section 2: what the ground is made of, whose images join set 1.
    GroundMaterials m_materials;
```

and a public accessor goes after `TreeInCell`, for the panel (section 2) and
for what later chapters plant:

```cpp
    // Chapter 38 section 2: what the ground is made of, for the panel and for what is planted on it.
    const GroundMaterials& Materials() const { return m_materials; }
```

`TerrainSettings` grows the ground's switches in section 2. `HorizonDemo.h`
gains one private function, after `GoTo`:

```cpp
    void                 DrawGroundControls();                                 // Chapter 38: sections 2, 4, 5, 11
```

### Where everything lands

```text
Assets/Terrain/
  make_island.py           on `start`, already grown: footprints in erode, step 2b   section 1, appendix
  Island/IslandMaterials0.png, IslandMaterials1.png   what step 2b writes (on start)  section 1
  Ground/<Layer>/Color.png, Normal.png, Height.png    six photographs (on start)      section 5
Source/PillowFort/UsdImport/
  UsdImport.h, .cpp        ImportRgbaImage8, beside ImportGrayImage16           section 2
Source/PillowFort/Demos/Horizon/
  GroundMaterials.h        the class, above
  GroundMaterials.cpp      the banner, the path line, the includes (section 2, grown in 4, 5, 6);
                           at file scope, above the namespace: transitionLayers, uploadLayers
                           (2), tintLayer (6), stretchHeight (8); in the namespace: MAP_FILES
                           (2), GROUND_COLORS (6); Initialize, Shutdown, LoadMap (2),
                           LoadTextures (5), and WeightsAt (4) last
  Terrain.h, .cpp          Chapters 36 and 37's, grown: the materials, the island's
                           set and the switches' flags (section 2)
  HorizonDemo.h, .cpp      the Ground header (section 2, grown in 4, 5, 11), the
                           views (section 4)
Shaders/Horizon/
  HorizonTypes.h           the flags and the false colours (section 2); six
                           colours (section 3); the reads' colours (section 11)
  TerrainHeight.glsl       set 1's other bindings                                sections 2, 5
  GroundMaterials.glsl     everything about materials, an include, grown in every section
  Terrain.frag.glsl        constants after GLINT_POWER: FLOOR_DEPTH (section 3),
                           DETAIL_NEAR, DETAIL_FAR (section 10); main grows;
                           waterColor takes the floor's colour                   sections 2-11
```

GLSL needs a name declared before it is used, so the constants all sit
together at the top, and a function sits above every function that calls it;
each section below says what it goes after.

---

# Part 1 — What the ground is made of (sections 1-4)

Part 1 needs nothing downloaded: the script's map is on `start`, the GPU loads
it, and the terrain is painted by it, from a distance first, because the far
view is what every later part must still match.

Every run in this chapter is with the engine's sky on, as in Chapters 36 and 37
(Chapter 35 section 7 says where to set **Sun sky**), and with the Tone mapping
window collapsed, with the triangle at the left of its title bar: this chapter
counts pixels of everything the other windows leave.

## 1. Erosion's footprints

**This is the material map: what it holds, the rules that made it, and its two
files.** The part of `make_island.py` that writes it is the Appendix at the end
of the chapter. Both files are on the `start` branch beside the heightmap, in
`Assets/Terrain/Island/`, so you can read this section, open them, and go
straight on to section 2. To make your own, the Appendix says how to run the
script.

> **Jump:** this section goes back to Chapter 36 section 7's erosion, and shows
> no code: the Appendix has the script's excerpts. Keep in mind only what it
> hands over: two images of 1,024 x 1,024 texels over the heightmap's square, each
> texel three of six weights, sand, grass and soil in the first, scree, rock
> and snow in the second.

### Six weights that add up to 1

A **material map** says what the ground is made of. The simplest one would
hold one material per texel, a number from 0 to 5. It cannot be filtered:
halfway between a sand texel (0) and a rock texel (4) the sampler returns 2,
which is soil, a material neither side has; and a mip level of an index is
nonsense. So each texel holds **a weight per material**, how much of it is
there, and the weights of a texel add up to 1: a texel of a beach turning to
grass might be 0.5 sand, 0.25 grass, 0.25 soil.

Weights can be filtered. A bilinear sample is a weighted average of four
texels, and the averaging weights themselves add up to 1, so if every texel's
six weights add up to 1, so do the sample's: each material's weight in the
sample is the average of its weights in the four texels, and the six averages
add up to the average of four 1s. A mip level is the same average over 2 x 2
texels. So at any distance and any filtering, the map says "this much of
each", and a far pixel covering a beach and a meadow gets some of both.

Stored in 8 bits, a weight is rounded, each on its own. A texel of 0.5, 0.25
and 0.25 is stored as 128, 64 and 64, which add up to 256, not 255; another
texel may come to 254. With six weights the sum lies between 252 and 258.
Dividing by the sum puts it right, and costs nothing: 128 / 256 = 0.500,
64 / 256 = 0.250. The shader and the CPU's copy both do it.

### Where the water went

What a cell is made of depends mostly on two things the heightmap alone does
not say: where the water ran, and where it dropped what it carried. Chapter
36's raindrops know both. `erode` already moves each drop a cell at a step and
works out `amount`, the soil it drops (positive) or picks up (negative); it
only has to write down, for the cell the drop is nearest to, that a drop
passed there, and how much it dropped. The passes run from coarse to fine, so
after the erosion step the counts are the finest pass's, on the 32 m work grid
the map is made on. Recording them must not change one byte of `Island.png`,
which Chapters 36 and 37 measured everything on; the Appendix says how.

### What each cell is made of

A new step of the script, 2b, classifies every cell of the 1,024 x 1,024 work
grid. It has four signals, each a grid of the same size: the height `h` in
metres; the slope `s` in metres up per metre across, from the cells on either
side; `v`, the drop steps through each cell, averaged over the 3 x 3 cells
around it and counted per drop per cell, so the numbers mean the same whatever
the number of drops; and `d`, the soil dropped, in metres, averaged the same
way twice. A fifth, `n`, is how much of the 13 x 13 cells around (416 m
square) is cliff, steeper than 0.8. Each material is a smooth mask from 0 to
1, Chapter 16 section 5's `smoothstep`, written `ss` here, worked once for a
cell where it is exactly a half:

- **Soil** where many drops ran, so only along the main streams:
  `ss(150, 420, v)`, the script's `SOIL_FROM` and `SOIL_TO`. A stream cell
  whose 3 x 3 cells saw 285 drop steps each, on average, is
  (285 − 150) / 270 = 0.5 of the way, so 0.5 soil. Lower bounds bring back the
  smaller streams and widen the main ones.
- **Scree** where soil settled below cliffs: `ss(0.04, 0.30, n) × (0.25 + 0.75
  × ss(10, 70, d))`. With 17 % of the cells around being cliff and 40 m of soil
  dropped, both are halfway, 0.5 × (0.25 + 0.375) = 0.31.
- **Rock** on the steep, and bare ground high up: `r = ss(0.65, 1.05, s)`,
  then `r + (1 − r) × 0.5 × ss(640, 800, h)`, half of what is not yet rock
  turning to rock between 640 and 800 m. A slope of 0.85, about 40 degrees
  (tan 40° = 0.84), is 0.5 rock; gentle ground (r = 0) at 720 m is
  0.5 × 0.5 = 0.25.
- **Snow** on the high tops, where it does not slide off: `ss(700, 820, h) ×
  (1 − ss(0.9, 1.3, s))`. At 760 m on a slope of 1.1, 0.5 × 0.5 = 0.25.
- **Sand** by the sea, on gentle ground: `(1 − ss(2.5, 9, h)) × (1 −
  ss(0.12, 0.30, s))`. Flat ground 5.75 m above the sea is 0.5 sand. Every cell
  below the sea is pure sand: the sea floor, which the shallows show.
- **Grass** is what is left.

The six are made to add up to 1 by **painting them in order**, each mask laid
over what is already there: grass first, covering everything; then soil,
which takes its share and leaves (1 − soil) of what was there; then scree,
rock, snow, and sand last. A cell with 0.5 soil and 0.2 sand ends 0.2 sand,
0.4 soil and 0.4 grass, which add up to 1, and they always will: each coat
takes from the others exactly what it adds. The order decides which wins where
two overlap: sand over snow, never the other way.

### Two files

The six weights go into **two ordinary RGB images**, 8 bits a channel, 1,024
texels a side over the heightmap's 32,768 m, so 32 m a texel, rows running +z
down the image and columns +x, as the heightmap's do. `IslandMaterials0.png`
holds sand, grass and soil in red, green and blue; `IslandMaterials1.png`
holds scree, rock and snow. Weight *i* is in file *i* / 3, channel *i* % 3, and
the photographs of section 5 use the same order. Why this shape:

- six weights need two images, whatever their format;
- all six are stored, none left implied as "whatever the others leave", so the
  shader divides by their sum and nothing else;
- no weight sits in an alpha channel, which image editors treat as
  transparency: some throw away the colour wherever alpha is 0;
- and each file opens in any image viewer as a picture that can be checked by
  eye.

Open `IslandMaterials0.png`: a green island, with a few blue streams down its
main valleys, in a red square, because the sea and the beaches are sand; black
where the mountains are, whose scree and rock are in `IslandMaterials1.png`,
red and green on black. The land is four-fifths grass (81 %), with 7 % sand,
6 % rock, 4 % scree and 2 % soil; snow is rare, 0.04 %, about 0.15 km² on the
highest gentle ground, because above 820 m almost everything is steeper than
snow can hold.

**A map from another tool.** Gaea and World Machine export masks for flow,
deposits, slope and altitude beside their heightmaps. To use them, write
their six weights into the two files' channels in this order, scaled so that
each texel's six add up to 255, at any size over the heightmap's square.
That is the whole contract.

## 2. The map on the GPU, and the island's set

**This is `ImportRgbaImage8`; the top of `GroundMaterials.cpp`,
`transitionLayers`, `uploadLayers`, `MAP_FILES`, `LoadMap`, `Initialize` and
`Shutdown`; the materials in `Terrain`; then the island's set, the map read
and drawn in false colours, the four switches, and the Ground header.**

### Decoding it

The map is decoded as the heightmap is, by the importer and the `stb_image`
inside TinyUSDZ (Chapter 36 section 8), which hands back four channels whatever
the file holds. Chapter 36's function keeps one of them at 16 bits; this one
keeps all four at 8, which section 5's photographs will need too: an 8- or
16-bit file, grey, RGB or RGBA, comes back as red, green, blue and alpha, with
grey copied into all three and a missing alpha 255. In `UsdImport.h`, after
`ImportGrayImage16`:

```cpp
// Chapter 38: an image of four 8-bit channels, such as a material map or a photograph to prepare on the CPU.
struct RgbaImage8
{
    uint32_t             width  = 0;
    uint32_t             height = 0;
    std::vector<uint8_t> texels;   // row by row from the top: red, green, blue, alpha for each of width * height
};

// Chapter 38: decodes an 8- or 16-bit gray, RGB or RGBA PNG to four 8-bit channels, as ImportGrayImage16
// does. Gray comes back in red, green and blue; a missing alpha is 255; 16 bits are rounded to 8. Fails,
// leaving `image` empty, when the file is missing or does not decode.
InitializationResult ImportRgbaImage8(const std::filesystem::path& file, RgbaImage8& image);
```

and in `UsdImport.cpp`, after `ImportGrayImage16`, the function is Chapter 36
section 8's copied and changed in four places. The file is read, decoded and
checked for errors by the same lines; only what it keeps differs. Its name and
comment first:

```cpp
// Chapter 38. The same door as ImportGrayImage16; TinyUSDZ's four channels are kept, at 8 bits each.
InitializationResult ImportRgbaImage8(const std::filesystem::path& file, RgbaImage8& image)
```

The format check takes 8 or 16 bits and requires all four channels, in place of
the `if (source.format != ...` condition and its message:

```cpp
    if (source.format != tinyusdz::Image::PixelFormat::UInt || (source.bpp != 8 && source.bpp != 16) ||
        source.channels != 4)
    {
        return InitializationResult::failure(std::format("{} is not an 8- or 16-bit image.", toUtf8(file.filename())));
    }
```

The texels are four bytes each, in place of the `image.texels.resize(...)` line:

```cpp
    image.texels.resize(size_t(image.width) * image.height * 4);
```

and the copy replaces everything from the line that begins
`const uint16_t* wide` to the end of the `for` loop, before
`return InitializationResult::success();`. A 16-bit channel is rounded to the
nearest 8-bit value, as Chapter 15's textures are:

```cpp
    if (source.bpp == 8)
    {
        std::copy_n(source.data.begin(), image.texels.size(), image.texels.begin());
    }
    else
    {
        // 16 bits per channel, native byte order: the nearest 8-bit value, as Chapter 15's textures round.
        const uint16_t* wide = reinterpret_cast<const uint16_t*>(source.data.data());
        for (size_t i = 0; i < image.texels.size(); ++i)
        {
            image.texels[i] = static_cast<uint8_t>((wide[i] + 128u) / 257u);
        }
    }
```

### An image of two layers

On the GPU the map is **one image of two layers**, Chapter 17 section 3's kind
of image: a stack of same-sized images under one handle, read in the shader
through a `sampler2DArray` with the layer as one more coordinate, as Chapter
17 section 6 reads its cascades. One image, not two, because the two halves of
the map are always read together, at the same uv, with the same sampler.

Its format is `R8G8B8A8_UNORM`, and **never `_SRGB`**. An `_SRGB` image is
decoded as colour when it is sampled (Chapter 08 section 4): a stored 128 would
come back as 0.216 instead of 0.502, and a beach half sand would read a fifth
sand. Weights are numbers, not colours. Alpha is unused, 255 everywhere. With
its mip levels, 1,024 down to 1, eleven of them, the image is 10.7 MiB.

Vulkan requires every device to sample, filter and blit `R8G8B8A8_UNORM` and
`_SRGB` images, so unlike Chapter 36's `R16_UNORM` there is nothing to ask.

The upload is the third copy of one pattern, a staging buffer, a copy into
level 0 and a blit per mip level: Chapter 15's `uploadTexture` (in
`GpuTexture.cpp`) wrote it first and Chapter 36's `UploadHeightmap` second.
Moving it into one shared function waits for a fourth copy; this one is
`UploadHeightmap` with a **layer count**. Four things change, each one line:

- the layers lie back to back in the staging buffer, so **one copy** with
  `layerCount = layers` fills level 0 of all of them;
- **one blit per level** makes that level in every layer: a blit's source and
  destination may cover several layers of an array image, each layer made from
  the same layer above it;
- every barrier's range covers all the layers: a barrier over layer 0 alone
  would leave the others in their old layout;
- the view is `VK_IMAGE_VIEW_TYPE_2D_ARRAY`.

It is a function at file scope, because section 5 calls it twice more for the
photographs, and it takes the stages that will read the image once it is made,
`readers`, for barrier (3). `GroundMaterials.cpp` begins with the includes this
section uses; sections 4, 5 and 6 add one or two each:

```cpp
///========================================================
/// @author Gary Yang
/// @brief  Chapter 38: what the ground is made of: the island's material map, and six photographs of it
/// @copyright (C) Gary 2026
///========================================================

// Source/PillowFort/Demos/Horizon/GroundMaterials.cpp
#include "PillowFort/Demos/Horizon/GroundMaterials.h"

#include "PillowFort/ErrorReporting/Log.h"
#include "PillowFort/UsdImport/UsdImport.h"
#include "PillowFort/VulkanGraphics/ExecutableFiles.h"

#include <algorithm>
#include <bit>
#include <cstring>
#include <filesystem>
#include <format>
#include <utility>
```

Its barrier helper, `transitionLayers`, is Chapter 36's `transitionLevels`
copied under its new name, at file scope, with a layer count: a `uint32_t
layers` parameter after `levels`, so that its comment and the signature's first
two lines are:

```cpp
// File scope, above the namespace block. Section 2: Chapter 36's transitionLevels, for every layer of an
// image at once.
static void transitionLayers(VkCommandBuffer commandBuffer, VkImage image, uint32_t firstLevel, uint32_t levels,
                             uint32_t layers, VkImageLayout oldLayout, VkImageLayout newLayout,
```

and `layers` in place of the 1 that ends the barrier's `subresourceRange`:

```cpp
        .subresourceRange    = { VK_IMAGE_ASPECT_COLOR_BIT, firstLevel, levels, 0, layers },
```

```cpp
// File scope, above the namespace block. Section 2: the upload with a mip chain a third time, after Chapter 15's
// uploadTexture and Chapter 36's UploadHeightmap, now with a layer count. `pixels` holds `layers` square images
// of `side` x `side` texels of four bytes, one after the other; `out` becomes an image of that many layers with
// every mip level, made on the GPU, and its 2D_ARRAY view. `readers` are the stages that sample it once made.
static InitializationResult uploadLayers(pf::vulkan_graphics::VulkanContext& context, VkFormat format,
                                         uint32_t side, uint32_t layers, const uint8_t* pixels,
                                         VkPipelineStageFlags2 readers, pf::demos::horizon::LayeredImage& out)
{
    using namespace pf::vulkan_graphics;
    const uint32_t levels = std::bit_width(side);   // 1,024 down to 1: 11 levels
    const VkImageCreateInfo imageInfo{
        .sType         = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO,
        .imageType     = VK_IMAGE_TYPE_2D,
        .format        = format,
        .extent        = { side, side, 1 },
        .mipLevels     = levels,
        .arrayLayers   = layers,
        .samples       = VK_SAMPLE_COUNT_1_BIT,
        .tiling        = VK_IMAGE_TILING_OPTIMAL,
        .usage         = VK_IMAGE_USAGE_TRANSFER_SRC_BIT | VK_IMAGE_USAGE_TRANSFER_DST_BIT | VK_IMAGE_USAGE_SAMPLED_BIT,
        .sharingMode   = VK_SHARING_MODE_EXCLUSIVE,
        .initialLayout = VK_IMAGE_LAYOUT_UNDEFINED,
    };
    const VmaAllocationCreateInfo allocationInfo{ .usage = VMA_MEMORY_USAGE_AUTO };
    if (vmaCreateImage(context.allocator, &imageInfo, &allocationInfo, &out.image, &out.allocation, nullptr) != VK_SUCCESS)
    {
        return InitializationResult::failure("vmaCreateImage failed for a ground image.");
    }

    // The layers back to back, as `pixels` holds them: one copy region covers them all.
    const VkDeviceSize size    = VkDeviceSize(side) * side * 4 * layers;
    AllocatedBuffer    staging = createBuffer(context, size, VK_BUFFER_USAGE_TRANSFER_SRC_BIT, true);
    std::memcpy(staging.mapped, pixels, static_cast<size_t>(size));
    vmaFlushAllocation(context.allocator, staging.allocation, 0, VK_WHOLE_SIZE);   // no-op if coherent

    immediateSubmit(context, [&](VkCommandBuffer commandBuffer) {
        // (1) What is written: every level of every layer, by the copy or a blit. Who reads it next: nothing
        //     yet. The layout: from nothing to TRANSFER_DST.
        transitionLayers(commandBuffer, out.image, 0, levels, layers,
                         VK_IMAGE_LAYOUT_UNDEFINED, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
                         VK_PIPELINE_STAGE_2_NONE, VK_ACCESS_2_NONE,
                         VK_PIPELINE_STAGE_2_COPY_BIT | VK_PIPELINE_STAGE_2_BLIT_BIT, VK_ACCESS_2_TRANSFER_WRITE_BIT);

        const VkBufferImageCopy region{
            .imageSubresource = { VK_IMAGE_ASPECT_COLOR_BIT, 0, 0, layers },
            .imageExtent      = { side, side, 1 },
        };
        vkCmdCopyBufferToImage(commandBuffer, staging.buffer, out.image, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, 1,
                               &region);

        int32_t above = static_cast<int32_t>(side);
        for (uint32_t level = 1; level < levels; ++level)
        {
            // (2) What was written: the level above, in every layer, by the copy or the blit before. Who reads
            //     it next: this blit. The layout: TRANSFER_DST to TRANSFER_SRC.
            transitionLayers(commandBuffer, out.image, level - 1, 1, layers,
                             VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,
                             VK_PIPELINE_STAGE_2_COPY_BIT | VK_PIPELINE_STAGE_2_BLIT_BIT, VK_ACCESS_2_TRANSFER_WRITE_BIT,
                             VK_PIPELINE_STAGE_2_BLIT_BIT, VK_ACCESS_2_TRANSFER_READ_BIT);

            // One blit makes this level in every layer: each layer from the same layer above it.
            const int32_t half = std::max(above / 2, 1);
            const VkImageBlit blit{
                .srcSubresource = { VK_IMAGE_ASPECT_COLOR_BIT, level - 1, 0, layers },
                .srcOffsets     = { { 0, 0, 0 }, { above, above, 1 } },
                .dstSubresource = { VK_IMAGE_ASPECT_COLOR_BIT, level, 0, layers },
                .dstOffsets     = { { 0, 0, 0 }, { half, half, 1 } },
            };
            vkCmdBlitImage(commandBuffer, out.image, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,
                           out.image, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, 1, &blit, VK_FILTER_LINEAR);
            above = half;
        }

        // (3) What was written: the last level, by the last blit (or, for a one-texel image, by the copy); the
        //     levels above it were only read since. Who reads it next: whatever samples the island, in a later
        //     submission, `readers`. The layouts: every level of every layer to SHADER_READ_ONLY.
        if (levels > 1)
        {
            transitionLayers(commandBuffer, out.image, 0, levels - 1, layers,
                             VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                             VK_PIPELINE_STAGE_2_BLIT_BIT, VK_ACCESS_2_NONE,
                             readers, VK_ACCESS_2_SHADER_SAMPLED_READ_BIT);
        }
        transitionLayers(commandBuffer, out.image, levels - 1, 1, layers,
                         VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL,
                         VK_PIPELINE_STAGE_2_COPY_BIT | VK_PIPELINE_STAGE_2_BLIT_BIT, VK_ACCESS_2_TRANSFER_WRITE_BIT,
                         readers, VK_ACCESS_2_SHADER_SAMPLED_READ_BIT);
    });
    destroyBuffer(context, staging);

    const VkImageViewCreateInfo viewInfo{
        .sType            = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO,
        .image            = out.image,
        .viewType         = VK_IMAGE_VIEW_TYPE_2D_ARRAY,
        .format           = format,
        .subresourceRange = { VK_IMAGE_ASPECT_COLOR_BIT, 0, levels, 0, layers },
    };
    if (vkCreateImageView(context.device, &viewInfo, nullptr, &out.view) != VK_SUCCESS)
    {
        return InitializationResult::failure("vkCreateImageView failed for a ground image.");
    }
    return InitializationResult::success();
}
```

Barriers (1) and (2) answer Chapter 04 section 5's three questions as Chapter
36's did, for every layer at once, and Chapter 36's control still fires here:
take `VK_ACCESS_2_TRANSFER_WRITE_BIT` out of barrier (2)'s first half, and
synchronization validation reports ten `SYNC-HAZARD-WRITE-AFTER-WRITE` at
`vkCmdPipelineBarrier2`, one after the copy and nine after blits. Barrier (3)
waits for `readers`, which `Initialize` passes as `ISLAND_READERS`; "The
island's set", below, says why.

### Loading it

The namespace opens after the file-scope functions, with the `using` of
`vulkan_graphics` that `Terrain.cpp` has too, and the files' names go at its
top:

```cpp
namespace pf::demos::horizon {

using namespace vulkan_graphics;

// Section 2: the material map Assets/Terrain/make_island.py writes beside the heightmap: two RGB files, three
// weights each, in Assets/Terrain/Island/ beside the executable.
constexpr std::array<const char*, 2> MAP_FILES{ "IslandMaterials0.png", "IslandMaterials1.png" };
```

`LoadMap` decodes both into one buffer, layer 0 then layer 1, which is how
`uploadLayers` wants them and how `WeightsAt` (section 4) will read them. A
missing or unreadable file, or two files of different sizes, is a warning, not
an error, as the heightmap's is: a one-texel stand-in of two layers keeps the
set valid, and `MapSize` says 0, which the terrain turns into "draw Chapter
37's ground". The CPU keeps level 0 of both layers, 8 MiB:

```cpp
// Section 2: the two files, decoded by the importer, one after the other in m_mapTexels: layer 0 (sand, grass,
// soil), then layer 1 (scree, rock, snow). Anything wrong is reported, not fatal: a one-texel stand-in of two
// layers keeps the set valid, and the terrain draws Chapter 37's ground.
void GroundMaterials::LoadMap()
{
    const std::filesystem::path folder = executableDirectory() / "Assets" / "Terrain" / "Island";
    m_mapTexels.clear();
    for (const char* name : MAP_FILES)
    {
        usd_import::RgbaImage8 image;
        if (auto result = usd_import::ImportRgbaImage8(folder / name, image); !result)
        {
            Log::warning(std::format("No material map: {} The ground keeps Chapter 37's colours.", result.message()).c_str());
            break;
        }
        if (image.width != image.height || (!m_mapTexels.empty() && image.width != m_mapSize))
        {
            Log::warning(std::format("No material map: {} is {} x {}, not square or not the other's size.", name,
                                     image.width, image.height).c_str());
            break;
        }
        m_mapSize = image.width;
        m_mapTexels.insert(m_mapTexels.end(), image.texels.begin(), image.texels.end());
    }
    m_hasMap = m_mapTexels.size() == size_t(m_mapSize) * m_mapSize * 4 * 2 && m_mapSize > 0;
    if (m_hasMap)
    {
        Log::info(std::format("Material map: {} x {} texels of {} m, 6 weights.", m_mapSize, m_mapSize,
                              m_mapMetres / static_cast<float>(m_mapSize)).c_str());
        return;
    }
    m_mapSize   = 1;
    m_mapTexels = { 0, 255, 0, 255, 0, 0, 0, 255 };   // grass, in both layers' order
}
```

`Initialize` is, for now, the map alone; section 5 adds the photographs before
its `return`:

```cpp
InitializationResult GroundMaterials::Initialize(const VulkanContext& context, float mapMetres)
{
    m_context   = context;
    m_mapMetres = mapMetres;

    // Section 2: the map, two layers. The GPU must read the weights as they are stored: UNORM, never SRGB.
    LoadMap();
    if (auto result = uploadLayers(m_context, VK_FORMAT_R8G8B8A8_UNORM, m_mapSize, 2, m_mapTexels.data(),
                                   ISLAND_READERS, m_map);
        !result)
    {
        return result;
    }
    return InitializationResult::success();
}
```

and `Shutdown` already destroys all three images: a handle that was never
made is null, and destroying a null handle does nothing, so it is safe after a
partial `Initialize`, and before section 5 has made the other two:

```cpp
void GroundMaterials::Shutdown()
{
    const VkDevice device = m_context.device;
    if (device == VK_NULL_HANDLE)
    {
        return;   // Initialize never ran
    }
    vkDestroySampler(device, m_layerSampler, nullptr);   // section 5
    for (LayeredImage* image : { &m_map, &m_colors, &m_normals })
    {
        vkDestroyImageView(device, image->view, nullptr);
        vmaDestroyImage(m_context.allocator, image->image, image->allocation);
    }
    *this = GroundMaterials{};
}
```

The namespace closes after the file's last function, with
`} // namespace pf::demos::horizon`. In `Terrain::Initialize`, the materials
go after the heightmap and before the set. The set's line is Chapter 36's as
it stands, and keeps its old name until "The island's set" renames it:

```cpp
    if (auto result = m_materials.Initialize(m_context, MAP_SIZE); !result) { return result; }   // Chapter 38 section 2
    if (auto result = CreateHeightmapSet(); !result) { return result; }         // section 9
```

and `Terrain::Shutdown` lets them go after the set:

```cpp
    vkDestroyDescriptorSetLayout(device, m_setLayout, nullptr);
    m_materials.Shutdown();                                        // Chapter 38 section 2
```

Two new files: regenerate (`GenerateProjects.bat`), then build. The log has a
new line, `Material map: 1024 x 1024 texels of 32 m, 6 weights.`, and the
picture has not changed: the map is on the GPU, and nothing reads it yet. If
the log says `No material map` instead, the two files are not beside the
executable: they are in `Assets/Terrain/Island/` on `start`; build again, which
copies `Assets/` again.

### The island's set

> **Jump:** Chapter 36's set 1 held the heightmap, for the vertex shader. From
> here it holds everything the island is made of, for any pass that reads it.
> Keep in mind the plan for the Horizon demo's sets, which every chapter from
> here follows: **set 0 is the frame** (the scene renderer's), **set 1 is the
> island**, and **set 2 is a pass's own**. A pipeline that needs set 2 but not
> the island still puts the island's layout at set 1, so the numbers never
> move.

Set 1 grows a binding for the map, and section 5 two more for the photographs:
binding 0 is still the heightmap; binding 1 the map, through the heightmap's
own sampler, which suits it exactly: linear, with linear mip levels, clamped
at the edge, and the map lies over the same square, so the same uv, and its
edge is sea too. Bindings 4 and up stay free; the coast will need one.

The terrain's vertex shader reads the heightmap and its fragment shader the
map; Chapters 39 to 41 will read both from compute shaders, to plant things.
So every binding of the island's set is visible to **all three stages**,
`ISLAND_STAGES`, and each image's last upload barrier waits for all three,
`ISLAND_READERS`. Barrier (3) answers "who reads it next" with "whatever
samples the island": a stage named there that never reads simply waits for
nothing, while a stage left out could read before the upload is visible. That
is the three questions' answer, not the fence's: as Chapter 36 section 8 found,
sync validation does not look across `immediateSubmit`'s fence wait, so this
barrier is argued, not checked.

`CreateHeightmapSet` becomes `CreateIslandSet`, in `Terrain.h`:

```cpp
    InitializationResult CreateIslandSet();                                      // Chapter 36 section 9; Chapter 38 section 2
```

and in `Terrain.cpp`, its bindings made in a loop and handed to Chapter 20
section 4's `createDescriptorSets`, as Chapter 36 handed it one. The pool it
counts from them is one set of as many combined image samplers as there are
bindings:

```cpp
// Chapter 36 section 9: set 1, written once: nothing in it changes after Setup. Chapter 38 section 2: the
// island's set, every image of the island a pass may sample: binding 0 the heightmap; 1 the material map,
// through the heightmap's sampler, since it lies over the same square and its edge is sea too. Every binding
// is visible to every stage that may read it (ISLAND_STAGES); the next ones are free.
InitializationResult Terrain::CreateIslandSet()
{
    std::array<VkDescriptorSetLayoutBinding, 2> bindings{};
    for (uint32_t binding = 0; binding < bindings.size(); ++binding)
    {
        bindings[binding] = {
            .binding         = binding,
            .descriptorType  = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER,
            .descriptorCount = 1,
            .stageFlags      = ISLAND_STAGES,
        };
    }
    if (!createDescriptorSets(m_context, bindings, m_setLayout, m_pool, { &m_set, 1 }))
    {
        return InitializationResult::failure("Creating the terrain's descriptor set failed.");
    }

    // One image for each binding, in binding order.
    const std::array<VkDescriptorImageInfo, 2> images{ {
        { m_heightmapSampler, m_heightmapView, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL },
        { m_heightmapSampler, m_materials.MapView(), VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL },
    } };
    std::array<VkWriteDescriptorSet, 2> writes{};
    for (uint32_t binding = 0; binding < writes.size(); ++binding)
    {
        writes[binding] = {
            .sType           = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET,
            .dstSet          = m_set,
            .dstBinding      = binding,
            .descriptorCount = 1,
            .descriptorType  = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER,
            .pImageInfo      = &images[binding],
        };
    }
    vkUpdateDescriptorSets(m_context.device, static_cast<uint32_t>(writes.size()), writes.data(), 0, nullptr);
    return InitializationResult::success();
}
```

`Terrain::Initialize` calls it by its new name, still after the materials,
whose images it points at:

```cpp
    if (auto result = CreateIslandSet(); !result)    { return result; }         // Chapter 36 section 9; Chapter 38 section 2
```

Chapter 36's heightmap is in the island's set too, so its barrier (3) widens
in the same way. In `UploadHeightmap`, both halves of it name
`ISLAND_READERS` as their destination stage, where they named the vertex
shader (`VK_PIPELINE_STAGE_2_VERTEX_SHADER_BIT`), and the comment above says
why: its "Who reads it next" becomes "whatever samples the island (Chapter 38
section 2), in a later submission".

The pipeline layout is still `{ frame, island }`, so `CreatePipeline` and
`Record`'s bind are unchanged. The shaders see the new binding where they see
binding 0, in `TerrainHeight.glsl`, which from now on declares the whole
island. Its header comment gains two lines at the end, after Chapter 36's own
three, which stay; the guard under them is as it was. Any pass that includes
the file names its push block's `TerrainDraw` `terrain`, first, because the
height functions read `terrain`, and the comment says so:

```glsl
// Shaders/Horizon/TerrainHeight.glsl - Chapter 36: the ground's height at any point, as the rings draw it.
// An include: Terrain.vert.glsl includes it after its TerrainDraw block, named `terrain`, which it reads.
// Terrain.cpp keeps a copy on the CPU (Terrain::HeightAt); change one and you must change the other.
// Chapter 38: it declares the whole of set 1, the island, so any pass that reads the island includes it, and
// declares `TerrainDraw terrain;` first in its push block.
#ifndef PF_HORIZON_TERRAIN_HEIGHT_GLSL
#define PF_HORIZON_TERRAIN_HEIGHT_GLSL
```

and binding 1 goes after binding 0's line:

```glsl
layout(set = 1, binding = 0) uniform sampler2D heightmap;

// Chapter 38 section 2: the material map, two layers of three weights, through the heightmap's sampler.
layout(set = 1, binding = 1) uniform sampler2DArray groundMap;
```

The fragment stage will see eight combined image samplers, set 0's bindings
4, 10, 11 and 12 and the island's four (after section 5), of the sixteen every
device must allow.

### The map, read

Everything about materials goes in one include, `GroundMaterials.glsl`, with
no bindings of its own, as `ForestDensity.glsl` has none: the images come in as
arguments, so a compute pass can use the same functions on the same set. Its
constants come first and its functions after them, each section saying where
its own go; it ends with the guard's `#endif`, and what is added here and in
later sections goes above that line. It begins with the order of the six, as
the map stores them, and a **false colour** for each, for the debug view below:

```glsl
// Shaders/Horizon/GroundMaterials.glsl - Chapter 38: what the ground is made of, from afar and up close. An
// include with no bindings of its own, as ForestDensity.glsl: the caller passes the island's images (set 1,
// declared in TerrainHeight.glsl). GroundMaterials::WeightsAt is the CPU's copy of groundWeights; change one
// and you must change the other.
#ifndef PF_HORIZON_GROUND_MATERIALS_GLSL
#define PF_HORIZON_GROUND_MATERIALS_GLSL

#include "HorizonTypes.h"       // MAP_ORIGIN, GROUND_*_FALSE

// Section 1: the six materials, in the order the map stores their weights and the photographs their layers.
const uint SAND  = 0u;
const uint GRASS = 1u;
const uint SOIL  = 2u;
const uint SCREE = 3u;
const uint ROCK  = 4u;
const uint SNOW  = 5u;

// Section 2: each material's false color, for the panel's "Show materials" (HorizonTypes.h).
const vec3 FALSE_COLORS[6] = vec3[](GROUND_SAND_FALSE.rgb, GROUND_GRASS_FALSE.rgb, GROUND_SOIL_FALSE.rgb,
                                    GROUND_SCREE_FALSE.rgb, GROUND_ROCK_FALSE.rgb, GROUND_SNOW_FALSE.rgb);
```

Chapter 36's `groundAlbedo` declares colours of its own named `SAND`, `GRASS`,
`ROCK` and `SNOW`. Inside that function they hide these indices, which GLSL
allows, and it uses no index.

The false colours themselves are in `HorizonTypes.h`, which C++ and GLSL
share, because section 4's readout writes each material's name in its colour;
as `vec4`, since the C++ side has no `vec3` alias there. After
`TERRAIN_SHOW_FOREST`:

```c
/* Chapter 38 section 2: each material's false colour, linear, for Show materials and the panel's readout. */
#define GROUND_SAND_FALSE   vec4(0.90f, 0.70f, 0.20f, 1.0f)
#define GROUND_GRASS_FALSE  vec4(0.10f, 0.60f, 0.10f, 1.0f)
#define GROUND_SOIL_FALSE   vec4(0.35f, 0.15f, 0.05f, 1.0f)
#define GROUND_SCREE_FALSE  vec4(0.80f, 0.10f, 0.80f, 1.0f)
#define GROUND_ROCK_FALSE   vec4(0.50f, 0.50f, 0.50f, 1.0f)
#define GROUND_SNOW_FALSE   vec4(1.00f, 1.00f, 1.00f, 1.0f)
```

The map's uv is `mapHeight`'s (Chapter 36 section 9), since the map covers the
heightmap's square; the two reads and the division by the sum are section 1's
weights:

```glsl
// Section 2: where xz lies on the material map: mapHeight's uv (Chapter 36 section 9), since the map covers
// the heightmap's square.
vec2 groundMapUv(vec2 xz, float mapSide)
{
    return (xz + MAP_ORIGIN) / mapSide + 0.5;
}
```

```glsl
// Section 2: the six weights at uv, from the map's two layers. Each stored weight was rounded on its own, so
// a texel's six add up to a little more or less than 1: dividing by their sum puts that right.
void groundWeights(sampler2DArray map, vec2 uv, out float w[6])
{
    vec3 first  = texture(map, vec3(uv, 0.0)).rgb;   // sand, grass, soil
    vec3 second = texture(map, vec3(uv, 1.0)).rgb;   // scree, rock, snow
    float sum = first.r + first.g + first.b + second.r + second.g + second.b;
    w[SAND]  = first.r / sum;
    w[GRASS] = first.g / sum;
    w[SOIL]  = first.b / sum;
    w[SCREE] = second.r / sum;
    w[ROCK]  = second.g / sum;
    w[SNOW]  = second.b / sum;
}
```

and the false colour is each material's, by its weight:

```glsl
// Section 2: the weights as false colors.
vec3 groundFalseColor(float w[6])
{
    vec3 color = vec3(0.0);
    for (uint i = 0u; i < 6u; ++i)
    {
        color += w[i] * FALSE_COLORS[i];
    }
    return color;
}
```

The fragment shader includes the island's set, from `TerrainHeight.glsl`, and
the new include, after `HorizonShading.glsl`:

```glsl
#include "TerrainHeight.glsl"     // Chapter 38 section 2: set 1, the island
#include "GroundMaterials.glsl"   // Chapter 38: what the ground is made of
```

`main` reads the weights first, after `V`, only while the flag
`TERRAIN_GROUND` is set. `texture()` takes its mip level from how fast the uv
changes between neighbouring pixels, which it can only see where every pixel
of a 2 x 2 quad runs the same code (section 6 says more); the flag is a push
constant, the same for every pixel, so the test keeps them all together:

```glsl
    // Chapter 38 section 2: what the ground is made of here. The push constant's flag is the same for every
    // pixel, so the map's implicit derivatives are fine inside the test.
    bool  ground = (terrain.flags & TERRAIN_GROUND) != 0u;
    float w[6];
    if (ground)
    {
        groundWeights(groundMap, groundMapUv(worldPosition.xz, terrain.heightmap.x), w);
    }
```

and after the haze, on the land, the false colours replace the picture while
`TERRAIN_SHOW_MATERIALS` is set. Like Chapter 36's ring view they come after
the haze, unlit, so a pixel's colour is exactly its weights' and can be read
back with a probe:

```glsl
    // Chapter 38 section 2: the map's weights on the land, as false colors.
    if ((terrain.flags & TERRAIN_SHOW_MATERIALS) != 0u && ground && groundHeight >= 0.0)
    {
        color = groundFalseColor(w);
    }
```

### The switches

The ground has four switches on the panel, each a bit of
`TerrainDraw::flags`, as Chapter 36's debug views are, so the push constants
do not change. They are all written here, once; each does something from the
section in the last column, and changes nothing before it:

| Switch | Flag | Default | What it does | From |
| --- | --- | --- | --- | --- |
| **Ground materials** | `TERRAIN_GROUND` | on | reads the map; off, Chapter 37's ground exactly, for comparing | 2, 3 |
| **Show materials** | `TERRAIN_SHOW_MATERIALS` | off | the map's weights as false colours | 2 |
| **Detail up close** | `TERRAIN_GROUND_DETAIL` | on | the photographs near the camera; off, the far colours there too | 6 |
| **Show reads** | `TERRAIN_SHOW_READS` | off | how many of this chapter's texture reads each pixel made | 11 |

In `HorizonTypes.h`, after `TERRAIN_SHOW_FOREST`:

```c
#define TERRAIN_GROUND          32u    /* Chapter 38 section 2: the material map is loaded and switched on */
#define TERRAIN_SHOW_MATERIALS  64u    /* Chapter 38 section 2: the map's weights, in false colours */
#define TERRAIN_GROUND_DETAIL   128u   /* Chapter 38 section 2: the photographs are loaded, and shown up close */
#define TERRAIN_SHOW_READS      256u   /* Chapter 38 section 2: how many ground reads each pixel makes */
```

In `TerrainSettings`, after `showForest`:

```cpp
    // Chapter 38 section 2: the ground's switches, each named with the section from which it does something.
    bool groundMaterials = true;    // sections 2, 3: off, Chapter 37's ground
    bool showMaterials   = false;   // section 2: the map's weights, in false colours
    bool groundDetail    = true;    // section 6: off, the far colours up close too
    bool showReads       = false;   // section 11: how many ground reads each pixel makes
```

and in `Terrain::Record`, after `TERRAIN_SKY`. The map is read only if it
loaded and while its switch is on, and the photographs only if they loaded too;
`TextureSize` is 0 until section 5 loads them, so **Detail up close** sets
nothing until then:

```cpp
    // Chapter 38 section 2: the map is read while it was loaded and the panel says so; the photographs, while
    // they were loaded too.
    const bool ground = m_materials.MapSize() > 0 && settings.groundMaterials;
    const bool detail = ground && m_materials.TextureSize() > 0 && settings.groundDetail;
    if (ground)                  { flags |= TERRAIN_GROUND; }
    if (settings.showMaterials)  { flags |= TERRAIN_SHOW_MATERIALS; }
    if (detail)                  { flags |= TERRAIN_GROUND_DETAIL; }
    if (settings.showReads)      { flags |= TERRAIN_SHOW_READS; }
```

### On the panel

The ground gets a header of its own in the Horizon panel, closed at first, and
below **Times**, so that nothing above it moves. `DrawPanel` calls it after
the objects' group:

```cpp
        DrawGroundControls();    // Chapter 38 section 2
```

It goes at the end of `HorizonDemo.cpp`, in the namespace. What was loaded
comes first, so that it is in view as soon as the header opens, and then the
switches:

```cpp
// Chapter 38: the ground's group, a header of its own below Times, closed at first, so that nothing above it
// moves.
void HorizonDemo::DrawGroundControls()
{
    if (!ImGui::CollapsingHeader("Ground"))
    {
        return;
    }
    // Section 2: what was loaded, at the top, in view as soon as the header opens.
    const GroundMaterials& materials = m_terrain.Materials();
    const uint32_t         mapSize   = materials.MapSize();
    if (mapSize > 0) { ImGui::Text("Map  %u x %u, 6 weights", mapSize, mapSize); }
    else             { ImGui::TextUnformatted("Map  none"); }

    // Section 2: the four switches.
    ImGui::Checkbox("Ground materials", &m_terrainSettings.groundMaterials);
    ImGui::SameLine();
    ImGui::Checkbox("Show materials", &m_terrainSettings.showMaterials);
    ImGui::Checkbox("Detail up close", &m_terrainSettings.groundDetail);
    ImGui::SameLine();
    ImGui::Checkbox("Show reads", &m_terrainSettings.showReads);
}
```

Run it. Open **Ground**: it reads **Map 1024 x 1024, 6 weights**. Tick **Show
materials**: the same island in the map's own colours, before anything is
painted. A few brown streams run down the main valleys of the green lowland,
two of them long lines toward the camera; the mountains are grey where they are
rock, a paler grey-green where the rock thins into grass, and magenta where
scree lies below their cliffs; a yellow rim of beach runs along the far coast,
and the sea keeps its own colour, because the false colours are for the land.
Each colour changes over a 32 m texel of the map, softened by the sampler's
filtering: this is the map exactly as it is stored.

## 3. Painting by the map

**This is six colours in `HorizonTypes.h`, `GroundMaterials.glsl` grown,
`waterColor`, and `main` grown.**

### Six colours

Chapter 36 painted the ground in four colours. The map has six materials, so
the four keep their colours, and soil and scree get two new ones: soil a dark
brown, scree a neutral grey lighter than the rock, because fresh broken stone
is paler than the weathered face above it. They are **linear**, and they are
what each material looks like from afar; section 6 tints every photograph so
that its average is exactly this. They go in `HorizonTypes.h`, after the false
colours:

```c
/* Chapter 38 section 3: what each material looks like from afar, linear: Chapter 36's sand, grass, rock and
   snow (the numbers its groundAlbedo keeps, for when there is no map), and soil and scree beside them. Section
   6 tints every photograph to have its material's color as its average. vec4, since the C++ side has no vec3
   here; alpha unused. */
#define GROUND_SAND_COLOR   vec4(0.45f, 0.40f, 0.28f, 1.0f)
#define GROUND_GRASS_COLOR  vec4(0.08f, 0.15f, 0.04f, 1.0f)
#define GROUND_SOIL_COLOR   vec4(0.10f, 0.07f, 0.04f, 1.0f)
#define GROUND_SCREE_COLOR  vec4(0.23f, 0.22f, 0.20f, 1.0f)
#define GROUND_ROCK_COLOR   vec4(0.22f, 0.19f, 0.15f, 1.0f)
#define GROUND_SNOW_COLOR   vec4(0.80f, 0.82f, 0.85f, 1.0f)
```

Chapter 36's `groundAlbedo` keeps its own literals for the ground with no map:
the same numbers, for sand, grass, rock and snow.

### The include grows

The six colours as an array, and how much the far colour varies (below), go
after the false colours:

```glsl
// Section 3: each material's color from afar (HorizonTypes.h), and how much the far color varies.
const vec3  GROUND_COLORS[6] = vec3[](GROUND_SAND_COLOR.rgb, GROUND_GRASS_COLOR.rgb, GROUND_SOIL_COLOR.rgb,
                                      GROUND_SCREE_COLOR.rgb, GROUND_ROCK_COLOR.rgb, GROUND_SNOW_COLOR.rgb);
const float VARIATION = 0.7;   // at most 70 % lighter or darker; within 36 % over nine tenths of the ground
```

and the variation uses Chapter 37's `valueNoise`, so the include takes its
file, after `HorizonTypes.h`:

```glsl
#include "ForestDensity.glsl"   // valueNoise (Chapter 37 section 6)
```

### Steeper than the map can see

The map's rock comes from slopes over 32 m. A ledge 10 m wide inside a cell
that is mostly gentle is not in it, yet it is plain to see: on the island, 21 %
of the 8 m texels steep enough for rock lie in cells the map calls something
else. The shader knows each pixel's slope from the vertex normal, so it adds
the rest: wherever the pixel is steeper than the script's band, 0.65 to 1.05
metres up per metre across, it is rock, and the other five make room in
proportion. The shader has the normal's `up`, its y, not the slope; a slope s
has a normal of (−s, 1, 0) before it is normalized, so

$$ \text{up} = \frac{1}{\sqrt{1 + s^2}} $$

and s = 0.65 gives 0.84, s = 1.05 gives 0.69. With `up` at 0.8,
`smoothstep(0.69, 0.84, up)` is t = (0.8 − 0.69) / 0.15 = 0.73 of the way, so
3t² − 2t³ = 0.82, and `1 − smoothstep` is 0.18: the pixel is 0.18 rock. If the
map already says more rock than that, nothing changes. The three functions of
this section, this one and the two below, go after `groundFalseColor`:

```glsl
// Section 3: rock wherever this pixel is steep, which the map's 32 m cells cannot see: ledges and gullies.
// `up` is the normal's y. The script's slope band, 0.65 to 1.05 metres up per metre across, is `up` from
// 0.84 down to 0.69. Where that says more rock than the map, the other five make room in proportion.
void addSteepRock(inout float w[6], float up)
{
    float steep = 1.0 - smoothstep(0.69, 0.84, up);
    if (steep > w[ROCK])
    {
        float rest = (1.0 - steep) / (1.0 - w[ROCK]);
        for (uint i = 0u; i < 6u; ++i)
        {
            w[i] *= rest;
        }
        w[ROCK] = steep;
    }
}
```

### From afar

The colour from afar is each material's colour, by its weight:

```glsl
// Section 3: the ground's color from afar: each material's color, by its weight.
vec3 groundFarColor(float w[6])
{
    vec3 color = vec3(0.0);
    for (uint i = 0u; i < 6u; ++i)
    {
        color += w[i] * GROUND_COLORS[i];
    }
    return color;
}
```

Six flat colours by a 32 m map leave large areas one even colour: a meadow is
a single green. A **variation** breaks it up into lighter and darker patches:
a gain around 1 that the far colour is multiplied by, from two octaves of
Chapter 37's value noise, 160 m and 40 m across, the second turned 37 degrees
so the two lattices do not line up, mixed six parts to four. `valueNoise` runs
from 0 to 1, so each octave less 0.5, and their mix, run from −0.5 to 0.5, and
the factor 2 in `2.0 * VARIATION * (...)` stretches that to −1 to 1: `VARIATION`
is the largest change either way. At 0.7 that is 70 % lighter or darker, which
value noise almost never reaches: over nine tenths of the ground the gain lies
within 36 % of 1. That sounds large, but the screen shows less: a 36 % gain in
linear light is about 15 % in the stored value (the sRGB curve compresses it),
and the haze dilutes it with distance, so from the viewpoint the patches come
out about 10 % lighter or darker on screen, plain to see and no more (the Exit
check measures it). Value noise averages 0.5 over any stretch a few waves wide,
so over wide ground the patches break up a meadow's colour without moving its
mean.

The variation must not alias far away, where one pixel covers more than a wave
of it, so each octave fades by **Chapter 36 section 3's rule, applied to the
ground a pixel covers**: an octave is whole while its wavelength spans four
footprints and gone by two. A pixel's **footprint** is how far the ground moves
from it to the next pixel, across or down, whichever is more: `dFdx` and `dFdy`
of the world position (Chapter 15 section 5's "How the sampler picks a level"),
the larger of their lengths. `main` takes the two once, as `dpx` and `dpy`, and
every read from section 6 on uses them. Worked: from the viewpoint, a pixel
looking at ground 3 km away covers about 11 m (1.07 mm for every metre of
distance in a window 1,080 pixels tall, so 3.2 m at 3 km, stretched along the
ground by the grazing view: from 878 m up the view meets it at a sine of
878 / √(878² + 3,000²) = 0.28, and 1 / 0.28 = 3.6), so the 40 m octave spans
3.6 footprints, `smoothstep(22, 44, 40)` is 0.91, and it is nearly whole; at
5 km a pixel covers 31 m and the 40 m octave is gone, while the 160 m octave is
still whole. Without the fade the 40 m octave would crawl out there as the
camera turns, a pattern finer than the pixels sampling it:

```glsl
// Section 3: a gain around 1 that makes the far color vary: two octaves of value noise, 160 m and 40 m across,
// the second turned 37 degrees. Each fades by Chapter 36 section 3's rule, against the ground a pixel covers
// (`footprint`, metres): whole while its wavelength spans four pixels, gone by two.
float groundVariation(vec2 xz, float footprint)
{
    vec2  turned = vec2(0.8 * xz.x - 0.6 * xz.y, 0.6 * xz.x + 0.8 * xz.y);
    float coarse = smoothstep(2.0 * footprint, 4.0 * footprint, 160.0) * (valueNoise(xz / 160.0) - 0.5);
    float fine   = smoothstep(2.0 * footprint, 4.0 * footprint, 40.0) * (valueNoise(turned / 40.0) - 0.5);
    return 1.0 + 2.0 * VARIATION * (0.6 * coarse + 0.4 * fine);
}
```

### Under the water

Chapter 36's sea shows its floor through shallow water, fading by
`exp(-depth / 3)`, and the floor was always sand. Now it is whatever the map
says, while it can be seen: down to `FLOOR_DEPTH`, 17 m, where exp(−17 / 3)
leaves 1/290 of it. Deeper, Chapter 36's sand, which saves the variation's
noise where nobody can see it. The depth is a constant in `Terrain.frag.glsl`,
after `GLINT_POWER`:

```glsl
// Chapter 38 section 3: how deep the sea floor still shows; below it, exp(-17 / 3) leaves 1/290 of it.
const float FLOOR_DEPTH = 17.0;   // metres
```

and `waterColor` takes the floor's colour as an argument in place of its own
sand. Three things change in the function as Chapter 37 section 8 left it. Its
comment gains a last line, and its signature the parameter `seaFloor`, in place
of the signature it had:

```glsl
// Chapter 38 section 3: `seaFloor`, the albedo of what lies below.
vec3 waterColor(float depth, vec3 V, float sunLit, vec3 seaFloor)
```

The line `vec3 sand  = groundAlbedo(0.0, 1.0);`, the floor at the waterline,
goes; and `body` mixes the deep colour with `seaFloor` where it mixed with
`sand`, in place of the line that began `vec3 body`:

```glsl
    vec3 body  = mix(DEEP, seaFloor, exp(-depth / 3.0)) * light;   // the floor fades out over a few metres
```

The rest is Chapters 36 and 37's water: the sky mirrored by Fresnel, and the
sun's glint, whose `// E` marks the sun's irradiance, the light arriving on a
surface facing it (Chapter 37 section 2).

### In `main`

After the weights, the derivatives and the footprint. They are taken outside
any branch, so every pixel of the quad has them:

```glsl
    // Chapter 38 section 3: how far the ground moves from this pixel to the next across and down, and so how
    // much ground one pixel covers, in metres.
    vec3  dpx       = dFdx(worldPosition);
    vec3  dpy       = dFdy(worldPosition);
    float footprint = max(length(dpx), length(dpy));
```

Under the water, the floor:

```glsl
    if (groundHeight < 0.0)
    {
        // Chapter 38 section 3: under shallow water, what the map says is there. Deeper, Chapter 36's sand,
        // which no one can see by then.
        vec3 seaFloor = groundAlbedo(0.0, 1.0);
        if (ground && -groundHeight < FLOOR_DEPTH)
        {
            float variation = groundVariation(worldPosition.xz, footprint);
            seaFloor = groundFarColor(w) * variation;
        }
        color = waterColor(-groundHeight, V, sunShadow(worldPosition, vec3(0.0, 1.0, 0.0), viewDepth), seaFloor);
    }
```

On land, Chapter 37's line stays for when there is no map, with the sun's
shadow taken out of it into a variable both branches use; with a map, rock
where the pixel is steep, and the far colour, varied:

```glsl
    else
    {
        vec3  N      = normalize(vertexNormal);
        float sunLit = sunShadow(worldPosition, N, viewDepth);   // Chapter 37 section 8, for either branch
        if (!ground)
        {
            color = groundAlbedo(groundHeight, N.y) * lightAt(N, sunLit);
        }
        else
        {
            // Chapter 38 section 3: the map's weights, rock wherever this pixel is steep, and the color from afar.
            addSteepRock(w, N.y);
            float variation = groundVariation(worldPosition.xz, footprint);
            vec3  albedo    = groundFarColor(w) * variation;
            color = albedo * lightAt(N, sunLit);
        }
    }
```

Run it, and press **Back to the viewpoint**. The island is the same shape, and
now made of something: thin brown streams run down the main valleys of the
green lowland, the mountains in the middle are pale grey rock with paler scree
spread below their cliffs, and a pale line of beach runs along the far coast on
the right. The snow caps are a few pixels from here; section 4's **Snow** view
goes to one. The green itself is no longer one green: it lies in lighter and
darker patches, a few dozen pixels across here, the darker ones like thicker
growth and the lighter like drier grass, about 10 % either way on screen (the
Exit check measures them). They stay on the ground as the view turns, with no
shimmer. **Show materials** looks as it did in section 2: from this high the
steep rock that `addSteepRock` adds covers a few dozen pixels.

## 4. Seeing it

**This is `WeightsAt` and the readout under the camera, and five places to
look from.**

### The CPU's copy

The panel says what the map says the ground under the camera is made of, and
Chapters 39 to 41 will ask the same question on the CPU to plant things. So
`groundWeights` gets a copy in C++, `WeightsAt`: Chapter 36 section 9's
`MapHeight`, a bilinear sample with the texel centres where the GPU puts them,
done for each of the six weights from level 0 of both layers, in the same
order of operations, then divided by the sum. It needs `MAP_ORIGIN`, so
`HorizonTypes.h` joins the includes:

```cpp
#include "Horizon/HorizonTypes.h"   // MAP_ORIGIN; section 3's GROUND_*_COLOR
```

`WeightsAt` is the file's last function, just above the namespace's closing
brace:

```cpp
// Section 4: groundWeights on the CPU, for the panel and for the chapters that plant on the island: Chapter 36
// section 9's MapHeight, a bilinear sample with the texel centres where the GPU puts them, for each of the six
// weights, then divided by their sum.
std::array<float, GROUND_LAYERS> GroundMaterials::WeightsAt(glm::vec2 xz) const
{
    const int       last  = static_cast<int>(m_mapSize) - 1;
    const glm::vec2 texel = ((xz + MAP_ORIGIN) / m_mapMetres + 0.5f) * static_cast<float>(m_mapSize) - 0.5f;
    const glm::vec2 base  = glm::floor(texel);
    const glm::vec2 f     = texel - base;
    auto value = [&](int x, int z, uint32_t weight) {
        x = std::clamp(x, 0, last);   // CLAMP_TO_EDGE
        z = std::clamp(z, 0, last);
        const size_t layer = weight / 3;
        const size_t index = ((layer * m_mapSize + static_cast<size_t>(z)) * m_mapSize + static_cast<size_t>(x)) * 4 + weight % 3;
        return static_cast<float>(m_mapTexels[index]) / 255.0f;
    };
    const int x = static_cast<int>(base.x);
    const int z = static_cast<int>(base.y);

    std::array<float, GROUND_LAYERS> weights{};
    float sum = 0.0f;
    for (uint32_t weight = 0; weight < GROUND_LAYERS; ++weight)
    {
        weights[weight] = glm::mix(glm::mix(value(x, z, weight), value(x + 1, z, weight), f.x),
                                   glm::mix(value(x, z + 1, weight), value(x + 1, z + 1, weight), f.x), f.y);
        sum += weights[weight];
    }
    for (float& weight : weights)
    {
        weight /= sum;
    }
    return weights;
}
```

These are the map's weights. The shader adds `addSteepRock` per pixel, which
the CPU's copy does not; on flat ground the two agree.

### Five places to look from

Five views, through Chapter 37's `GoTo`, each where one material is plain to
see, all within the 5 km disc: a beach, looking along it toward the
lighthouse; a meadow with no forest, from 25 m up so that the near and the far
ground are both in view (section 10 needs that); a stream, from beside its line
of soil; a rock face 50 m off; and the snow on a high ridge. They go above
`LEVEL_COLORS`, after an array of the false colours for the readout's labels:

```cpp
// Chapter 38 section 4: each material's false colour, for the readout's labels (HorizonTypes.h); and places
// to look at the ground from, each where one material is plain to see.
constexpr std::array<glm::vec4, GROUND_LAYERS> GROUND_FALSE{ GROUND_SAND_FALSE, GROUND_GRASS_FALSE, GROUND_SOIL_FALSE,
                                                             GROUND_SCREE_FALSE, GROUND_ROCK_FALSE, GROUND_SNOW_FALSE };
constexpr std::array<View, 5> GROUND_VIEWS{ {
    { "Shore", { 2265.0f, 1400.0f }, 2.0f, -15.0f, -6.0f },      // a beach, looking along it
    { "Meadow", { -80.0f, -208.0f }, 25.0f, 150.0f, -12.0f },  // grass, and no forest
    { "Stream", { 524.0f, -532.0f }, 2.0f, 45.0f, -5.0f },     // beside a line of soil
    { "Cliff", { -3495.0f, 820.0f }, 2.0f, 36.0f, 35.0f },     // a rock face, 50 m off
    { "Snow", { -4344.0f, 1312.0f }, 2.0f, -102.0f, 0.0f },    // on the snow of a high ridge
} };
```

In `DrawGroundControls`, after the switches, come the views, and the readout:
each material's name and weight under the camera, three to a line, each in
its false colour, so that the readout is also the key to **Show materials**.
ImGui's colours are sRGB, so each is encoded first, as Chapter 37's depth
readout does:

```cpp
    // Section 4: places to look from, and what the map says the ground under the camera is made of, each
    // material in its false colour, so that the readout is Show materials' key as well.
    for (const View& view : GROUND_VIEWS)
    {
        if (ImGui::Button(view.label)) { GoTo(view.xz, view.height, view.yaw, view.pitch); }
        ImGui::SameLine();
    }
    ImGui::NewLine();
    if (mapSize > 0)
    {
        const glm::vec3&                       position = m_cameraTransform.translation;
        const std::array<float, GROUND_LAYERS> weights  = materials.WeightsAt({ position.x, position.z });
        ImGui::TextUnformatted("Made of here, by the map:");
        for (uint32_t layer = 0; layer < GROUND_LAYERS; ++layer)
        {
            const glm::vec3 shown = scene::linearToSrgb(glm::vec3(GROUND_FALSE[layer]));
            if (layer % 3 != 0) { ImGui::SameLine(); }
            ImGui::TextColored(ImVec4(shown.r, shown.g, shown.b, 1.0f), "%s %.0f %%", GROUND_NAMES[layer],
                               100.0f * weights[layer]);
        }
    }
```

In a window 720 pixels tall the panel scrolls once **Ground** is open. From
section 5, which adds a line above the switches, the readout's second line is
below the panel's bottom edge; the mouse wheel over the panel brings it up.

## Checkpoint

The island painted by its map, with nothing downloaded. **Back to the
viewpoint**: streams, scree, rock and beaches, as in section 3. Open **Ground**
and tick **Show materials**: section 2's false colours, whose key is now the
readout's names. Tick **Show forest** beside it: the forest's dark green lies
over the green and the brown, on grass and soil, and stops at the grey.
**Stream**: the readout says Grass 62 % and Soil 38 %, and the false colours
run brown from the left into the distance, along the stream, green to the
right. **Snow**: the ridge under the camera reads Snow 99 %, and is white in
the false colours, with the grey rock of a steeper peak beyond it. Untick
**Ground materials**: Chapter 37's frame comes back.

---

# Part 2 — Up close (sections 5-8)

From a few metres up, Part 1's ground is still a painting: flat colour, and
every border a cross-fade as wide as a 32 m cell. Part 2 puts real ground under
the camera: six photographs, read where the camera is near, lit through their
normals, and meeting by height.

## 5. Six photographs

**This is the six layers on disk, `LoadTextures`, the photographs in
`Initialize` and in the island's set, and the panel's line.**

### What makes a good one

A ground texture for a whole island has more to do than look good in a square
of its own. Six things matter, in this order:

- **CC0**, so it can be committed and shipped with no conditions.
- **Seamless**: its right edge continues its left, and its top its bottom, so
  it can repeat.
- **De-lit**: no shadows or highlights baked in, because the engine lights it,
  from a sun that may be anywhere.
- **Of known real size**, so it can be laid at that size (section 6).
- **No single feature that marks the repeat.** A pale stone or a dark hollow in
  one corner shows up every tile, and in perspective the copies line up into
  rows. The test is the photograph tiled 4 x 4, and seen at a low angle.
- **A height map with spread**, for section 8's blend.

Two sites publish ground textures under CC0 with all three maps, ambientCG
and Poly Haven. These six were chosen by that list:

| Layer | Texture | Site | Real size | Linear mean as published |
| --- | --- | --- | --- | --- |
| Sand | Ground 055 L | ambientCG | 3.0 m | (0.345, 0.314, 0.223) |
| Grass | Grass 004 (generated) | ambientCG | 1.4 m | (0.127, 0.161, 0.034) |
| Soil | Ground 048 | ambientCG | 1.4 m | (0.105, 0.056, 0.038) |
| Scree | Gray Rocks, by Dimitrios Savva | Poly Haven | 1.8 m | (0.198, 0.174, 0.137) |
| Rock | Rock 045 | ambientCG | 2.4 m | (0.271, 0.258, 0.195) |
| Snow | Snow 006 | ambientCG | 2.5 m | (0.575, 0.580, 0.583) |

Five are photographs of real ground. **The grass is not**: Grass 004 is one
ambientCG made procedurally, in software, with no camera. Every photographed
grass on both sites repeated visibly, patches of light and dead blades that
line up into rows every couple of metres, and grass covers four-fifths of
the island, so its repeat would be in nearly every view; Grass 004 has no
feature larger than a blade. The chapter calls all six photographs, for short.

**Getting them.** On the `start` branch the eighteen files are already in
`Assets/Terrain/Ground/`, with the `.gitattributes` line and the notice rows
below in place: what follows is how they were chosen and fetched, and what to
do for photographs of your own. From ambientCG take each texture's **1K PNG**
download, a zip, and from it only three files:
`<Name>_1K-PNG_Color.png`, `<Name>_1K-PNG_NormalGL.png` and
`<Name>_1K-PNG_Displacement.png`, for `Ground055L`, `Grass004`, `Ground048`,
`Rock045` and `Snow006`; from Poly Haven, Gray Rocks' three 1K PNG files,
`gray_rocks_diff_1k.png`, `gray_rocks_nor_gl_1k.png` and
`gray_rocks_disp_1k.png`. Take the **GL** normal map, green up the image
(Chapter 15 section 10), not the DX one. Leave the rest of each zip, the
`.blend`, `.usdc`, `.mtlx` and `.tres` files, unopened. PNG, not JPG, because
the colour is tinted at load and a JPG would be compressed twice over.

**On disk** they go in `Assets/Terrain/Ground/`, a folder per layer, each
holding `Color.png`, `Normal.png` and `Height.png`, renamed and otherwise as
downloaded:

```text
Assets/Terrain/Ground/
  Sand/   Color.png  Normal.png  Height.png      from Ground055L
  Grass/  Color.png  Normal.png  Height.png      from Grass004
  Soil/   Color.png  Normal.png  Height.png      from Ground048
  Scree/  Color.png  Normal.png  Height.png      from gray_rocks
  Rock/   Color.png  Normal.png  Height.png      from Rock045
  Snow/   Color.png  Normal.png  Height.png      from Snow006
```

The build already copies `Assets/` beside the executable (Chapter 13 section
6). The routine for any third-party asset in this guide has three parts. The
files go in Git LFS, by folder as the heightmap's do (the eighteen are 61 MB),
with one more line at the end of `.gitattributes`:

```text
Assets/Terrain/Ground/** filter=lfs diff=lfs merge=lfs -text
```

`THIRD_PARTY_NOTICES.md` gets a row per asset at the end of its Assets table,
here six, one per layer, in the table's columns: what it is (`Ground texture:
Sand`), where it lies in the repository, the texture's name, author and site,
its licence, and what was changed, which is nothing in the files here: the
program tints and stretches them when it loads them. And where a licence asks
for its text to go with the files, as EZ-Tree's MIT licence does in Chapter 39,
the licence file sits beside them; CC0 asks for none, so the ground has none.
The paragraph above the table says `Assets/Terrain/Ground/`, beside
`ThirdPartyScenes/`, holds other people's work.

### Two images of six layers

On the GPU the photographs are **two images of six layers each**, colour and
normals, in the map's order. Why arrays, not eighteen separate images: eighteen
textures as separate bindings would pass the sixteen samplers every device
gives a stage; an array of separate textures indexed in a loop needs a device
feature the engine does not enable; in an image of layers, the layer is just a
coordinate.

The **colour** image is `R8G8B8A8_SRGB`: colour is stored sRGB-encoded and must
be decoded to linear when it is sampled, as Chapter 15's base colours are.
That matters for the mip levels too: a blit from an `_SRGB` image decodes to
linear before it averages, so each level is the true average of the light,
not of the encoded numbers. Its **alpha** is free for now; section 8 puts the
height there: an `_SRGB` format decodes red, green and blue and leaves alpha
linear, so the height will cost no image and no read of its own. The
**normal** image is `R8G8B8A8_UNORM`: a normal is data, and decoded as sRGB a
flat one would lean 39 degrees (Chapter 15 section 4).

Both are 1,024 x 1,024 x 6 with eleven mip levels, 32 MiB each; with the map,
75 MiB of GPU memory, where the heightmap alone is 43. Decoding and preparing
the map and the eighteen files, and making their mip levels, happens each time
the demo is entered.

### All or nothing

`LoadTextures` reads the eighteen files, layer by layer. Either all of them
load, or none is used: a missing file, or one of a different size, is one
warning, and one-texel stand-ins keep the set valid. The ground then keeps its
far colours up close too, which is Part 1's picture exactly, because the
terrain only reads the photographs while `TerrainDraw::flags` says they are
there. The height maps are read with the others, so that all eighteen are all
or nothing; section 8 puts them to use. `LoadTextures` goes after `LoadMap`:

```cpp
// Section 5: three files for each of the six materials, in Assets/Terrain/Ground/<Name>/, decoded one layer
// after another. All or nothing: if any file is missing or a size differs, one warning, and one-texel
// stand-ins that the terrain never blends.
void GroundMaterials::LoadTextures()
{
    const std::filesystem::path folder = executableDirectory() / "Assets" / "Terrain" / "Ground";
    m_colorTexels.clear();
    m_normalTexels.clear();
    m_textureSize = 0;
    std::string problem;
    for (uint32_t layer = 0; layer < GROUND_LAYERS && problem.empty(); ++layer)
    {
        std::array<usd_import::RgbaImage8, 3> images;   // colour, normal, height
        const std::array<const char*, 3> files{ "Color.png", "Normal.png", "Height.png" };
        for (size_t i = 0; i < files.size() && problem.empty(); ++i)
        {
            const std::filesystem::path file = folder / GROUND_NAMES[layer] / files[i];
            if (auto result = usd_import::ImportRgbaImage8(file, images[i]); !result)
            {
                problem = result.message();
            }
            else if (images[i].width != images[i].height || (m_textureSize != 0 && images[i].width != m_textureSize))
            {
                problem = std::format("{}/{} is {} x {}, not square or not the others' size.", GROUND_NAMES[layer],
                                      files[i], images[i].width, images[i].height);
            }
            else
            {
                m_textureSize = images[i].width;
            }
        }
        if (problem.empty())
        {
            m_colorTexels.insert(m_colorTexels.end(), images[0].texels.begin(), images[0].texels.end());
            m_normalTexels.insert(m_normalTexels.end(), images[1].texels.begin(), images[1].texels.end());
        }
    }
    m_hasTextures = problem.empty();
    if (m_hasTextures)
    {
        Log::info(std::format("Ground textures: {} layers of {} x {}.", GROUND_LAYERS, m_textureSize, m_textureSize).c_str());
        return;
    }
    Log::warning(std::format("No ground textures: {} The ground keeps its flat colours up close.", problem).c_str());
    m_textureSize = 1;
    m_colorTexels.assign(4 * GROUND_LAYERS, 128);   // grey, and a height of one half
    m_normalTexels.clear();
    for (uint32_t layer = 0; layer < GROUND_LAYERS; ++layer)
    {
        m_normalTexels.insert(m_normalTexels.end(), { 128, 128, 255, 255 });   // straight up
    }
}
```

`<string>` joins the includes, for the problem's message, and `GpuTexture.h`
for the sampler below:

```cpp
#include "PillowFort/VulkanGraphics/GpuTexture.h"
```

```cpp
#include <string>
```

`Initialize` grows the photographs after the map's upload and before its
`return`: their two uploads, the CPU's copies freed once the GPU holds them,
and Chapter 15's material sampler for both: repeating, trilinear, and as
anisotropic as the device allows, up to 16x:

```cpp
    // Section 5: the photographs. Their colours are sRGB, which the GPU decodes when it samples them and
    // when it blits their mip levels; alpha, the height (section 8), stays linear. Normals are data: UNORM.
    LoadTextures();
    if (auto result = uploadLayers(m_context, VK_FORMAT_R8G8B8A8_SRGB, m_textureSize, GROUND_LAYERS,
                                   m_colorTexels.data(), ISLAND_READERS, m_colors);
        !result)
    {
        return result;
    }
    if (auto result = uploadLayers(m_context, VK_FORMAT_R8G8B8A8_UNORM, m_textureSize, GROUND_LAYERS,
                                   m_normalTexels.data(), ISLAND_READERS, m_normals);
        !result)
    {
        return result;
    }
    m_colorTexels  = {};   // the CPU's copies, 48 MB: the GPU holds the photographs now
    m_normalTexels = {};

    // Chapter 15's material sampler: repeating, trilinear, as anisotropic as the device allows up to 16x.
    m_layerSampler = createMaterialSampler(m_context.device, m_context.physicalDevice, scene::TextureWrap::Repeat,
                                           scene::TextureWrap::Repeat);
    if (m_layerSampler == VK_NULL_HANDLE)
    {
        return InitializationResult::failure("vkCreateSampler failed for the ground's photographs.");
    }
```

### Into the island's set

`CreateIslandSet` grows from two bindings to four: its three arrays' `2`
become `4`, and the two photographs join the list of images, through their
sampler. Its comment names them, too: after "its edge is sea too" it gains
"; 2 and 3 the photographs (section 5)":

```cpp
    // One image for each binding, in binding order.
    const std::array<VkDescriptorImageInfo, 4> images{ {
        { m_heightmapSampler, m_heightmapView, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL },
        { m_heightmapSampler, m_materials.MapView(), VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL },
        { m_materials.LayerSampler(), m_materials.ColorView(), VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL },
        { m_materials.LayerSampler(), m_materials.NormalView(), VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL },
    } };
```

`TerrainHeight.glsl` declares them after the map: the map's comment gains a
second line, and bindings 2 and 3 follow binding 1's. The block repeats the
map's own line, so that the order is plain:

```glsl
// Chapter 38 section 2: the material map, two layers of three weights, through the heightmap's sampler.
// Section 5: the six photographs, one layer each: colour, with the height in alpha, and normals.
layout(set = 1, binding = 1) uniform sampler2DArray groundMap;
layout(set = 1, binding = 2) uniform sampler2DArray groundColors;
layout(set = 1, binding = 3) uniform sampler2DArray groundNormals;
```

and the panel says what was loaded, after the map's line:

```cpp
    const uint32_t textureSize = materials.TextureSize();
    if (textureSize > 0) { ImGui::Text("Ground textures  6 x %u x %u", textureSize, textureSize); }
    else                 { ImGui::TextUnformatted("Ground textures  none: flat colours"); }
```

Run it. The log has `Ground textures: 6 layers of 1024 x 1024.`, and
**Ground** reads **Ground textures 6 x 1024 x 1024** under the map's line. The
picture has not changed: the photographs are on the GPU, and nothing reads
them yet.

## 6. Tiling in metres, derivatives before branches, and a tint

**This is `GROUND_TILE` and `GROUND_TURN`, `Projection`, `topProjection`,
`readColor` and `groundDetail`, and their place in `main`; then `tintLayer`.**

### How big a texel is

A photograph is laid at its **real size**: Ground 055 L covers 3 m of beach, so
its 1,024 texels go on 3 m of the island, 2.9 mm each. Laid twice as large,
its grains of sand would be gravel; a tenth as large, dust. A pixel 3 m away,
in a window 1,080 pixels tall through Chapter 10 section 4's 60-degree lens,
spans 2 × 3 × tan 30° / 1,080 = 3.2 mm, so from 3 m away one texel is about
one pixel: that is as close as a photograph of this size holds up.

**Tiles that do not line up.** Each layer repeats every tile, in a square grid
on the ground. Laid straight, every layer's grid would run along the world's
axes, and along the 32 m map's cells, and the eye picks out lines that several
grids share. So each layer is **turned** by its own angle: two grids turned
against each other never line up, whatever their sizes, as long as the turns
do not differ by a multiple of 90 degrees, which brings a square grid back
onto itself. So each can be laid at exactly its real size. Rock is not turned,
because section 9 lays it three ways at once.

The real sizes are section 5's table; the sizes and turns, and the smallest
weight worth reading (below), are constants in `GroundMaterials.glsl`, after
`VARIATION`:

```glsl
// Section 6: how big each photograph is on the ground, in metres: its real size; and how far each is turned,
// in degrees, so that no two grids line up, nor one with the world's axes. Rock is not turned: section 9 lays
// it three ways at once.
const float GROUND_TILE[6] = float[](3.0, 1.4, 1.4, 1.8, 2.4, 2.5);
const float GROUND_TURN[6] = float[](23.0, 61.0, 137.0, 41.0, 0.0, 97.0);
const float MIN_WEIGHT     = 1.0 / 255.0;   // a weight under this is not read: less than the map can store
```

### A projection

Where a pixel falls in a layer's photograph, and how fast that changes from
one pixel to the next, is a **projection**: here, the photograph laid flat on
the ground, turned and scaled. The turn is a 2 x 2 rotation matrix R times the
ground position (x, z), Chapter 10 section 1's matrix times a vector:

$$ u = \frac{x \cos\theta - z \sin\theta}{\text{tile}}, \qquad v = \frac{x \sin\theta + z \cos\theta}{\text{tile}} $$

with θ the layer's turn. The same matrix turns `dpx` and `dpy`, the ground's
change to the next pixel, into the uv's. Section 7 will want one more thing
from it, the world direction in which u grows; for now the uv and its two
derivatives. The struct and its function go after `groundVariation`:

```glsl
// Section 6: where a pixel falls in a photograph: its uv, and how much the uv changes to the next pixel across
// and down.
struct Projection
{
    vec2 uv;
    vec2 dx;
    vec2 dy;
};
```

```glsl
// Section 6: a layer's photograph laid flat on the ground, turned and at its size. `dpx` and `dpy` are how
// far the ground moves from this pixel to the next across and down, taken before any branch.
Projection topProjection(uint layer, vec3 position, vec3 dpx, vec3 dpy)
{
    float turn     = radians(GROUND_TURN[layer]);
    mat2  rotation = mat2(cos(turn), sin(turn), -sin(turn), cos(turn));   // two columns
    float tile     = GROUND_TILE[layer];
    Projection p;
    p.uv   = rotation * position.xz / tile;
    p.dx   = rotation * dpx.xz / tile;
    p.dy   = rotation * dpy.xz / tile;
    return p;
}
```

### Derivatives before branches

> **Jump:** until now the shader has sampled with `texture()` and let the GPU
> choose the mip level. From here, every read is in a branch, and the shader
> passes the derivatives itself. Keep in mind why: the GPU learns how fast a uv
> changes by comparing it between the pixels of a 2 x 2 quad, so it needs all
> four of them running the same code at that moment.

`texture()` picks its mip level from the uv's **derivatives**, which it finds
by subtracting the uv of the pixel beside it in its 2 x 2 **quad** (Chapter 15
section 5). If a branch has sent the neighbour elsewhere,
there is nothing to subtract: the result is undefined, and on some GPUs a seam
of wrong mip levels runs along every border where the branch changes. This
shader will branch on which layers have weight, on distance, and on the rock's
sides; a single `texture()` inside any of them is wrong.

The cure is to take the derivatives once, **at the top of `main`**, before any
branch, while every pixel of the quad runs, and to pass them to every read.
`dpx` and `dpy`, which section 3 already takes for the footprint, say how far
the ground moves to the next pixel across and down; a projection turns them
into the uv's derivatives, as it turns the position into the uv, and
`textureGrad` reads with them, legal in any branch.

Two honest notes. `lightAt` (Chapter 37 section 2) has always sampled the
sky's diffuse cube with `texture()` inside the land branch; it was safe
because that cube has one mip level, so there is nothing to choose. These
arrays have eleven. And there is no firing control for this rule: lavapipe,
Mesa's software Vulkan driver that the harness runs on the CPU, computes every
pixel of a quad together, whatever the branches say, so on it the wrong code
gives the right picture. The rule stands on the specification, not on a
demonstration.

`readColor` goes after `topProjection`:

```glsl
// Section 6: one read of a layer's photograph: its color, linear, and in alpha its height (section 8). With
// the gradients passed in, it is legal in any branch.
vec4 readColor(sampler2DArray colors, uint layer, Projection p)
{
    return textureGrad(colors, vec3(p.uv, float(layer)), p.dx, p.dy);
}
```

### The blend

A pixel's albedo from the photographs is each layer's colour by its weight.
Weights under 1/255, less than the map can store, are not read. The colours are
read into an array first, and added up in a second loop, because section 8
puts a step between the two. `groundDetail` goes after `readColor`, and stays
the last function of the include but `readsColor`: what sections 7 to 9 add
goes between `readColor` and it, each section saying where:

```glsl
// Section 6: what the photographs show at a pixel: each material's color, by its weight.
vec3 groundDetail(sampler2DArray colors, float w[6], vec3 position, vec3 dpx, vec3 dpy)
{
    // Section 6: every material with a weight, its color read once.
    vec4 color[6];
    for (uint i = 0u; i < 6u; ++i)
    {
        color[i] = vec4(0.0);
        if (w[i] > MIN_WEIGHT)
        {
            color[i] = readColor(colors, i, topProjection(i, position, dpx, dpy));
        }
    }

    // The share each material shows: its weight, for now (section 8).
    float b[6] = w;

    vec3 albedo = vec3(0.0);
    for (uint i = 0u; i < 6u; ++i)
    {
        if (b[i] > MIN_WEIGHT)
        {
            albedo += b[i] * color[i].rgb;
        }
    }
    return albedo;
}
```

### In `main`

**Detail up close**, the switch from section 2, now does something: with the
photographs loaded, `Record` sets its flag, and `main` reads them. After the
footprint, `near` says how much of the photographs shows: all of it while the
flag is set, for now. Section 10 will fade it with distance:

```glsl
    // Section 6: how much of the photographs shows here: all of it, while the switch is on.
    float near = (terrain.flags & TERRAIN_GROUND_DETAIL) != 0u ? 1.0 : 0.0;
```

On land, after the far colour, the photographs' colour, varied the same way,
is mixed over it by `near`; these lines go between `albedo` and the last line,
which stays:

```glsl
            // Section 6: the photographs, while any of them shows.
            if (near > 0.0)
            {
                albedo = mix(albedo, groundDetail(groundColors, w, worldPosition, dpx, dpy) * variation, near);
            }
```

Under shallow water the floor is the sand's photograph, the one layer the
sea floor is made of: inside the floor's test, after `seaFloor` is set from
the map:

```glsl
            if (near > 0.0)
            {
                vec3 sand = readColor(groundColors, SAND, topProjection(SAND, worldPosition, dpx, dpy)).rgb;
                seaFloor  = mix(seaFloor, sand * variation, near);
            }
```

Run it, and press **Meadow**: the grass has a grain now, finest at the bottom
of the window. **Shore**: the sand runs on under the shallows, the water's
edge crossing it with no seam. Two things are still wrong, and sections 7 and
8 fix them: everything is lit as if flat, so the sand's ripples and the
scree's stones are paint; and where two materials meet, one photograph fades
into the other over 32 m, a blur at the meadow's edge and a smear of soil
along the stream.

Now press **Back to the viewpoint**. The island has changed colour. For now the
photographs are read everywhere, far ground too, through their mip levels, and
what they average to is their own, not the island's: the meadows are a yellower
olive, the streams redder, the rock paler. On the reference run a meadow pixel
below the summit, at (900, 600), goes from section 4's (70, 91, 75) to (83, 95,
73). Section 10 will stop reading them far away, but the same mismatch would
then draw a line where they stop. The cure is to make each photograph average
to its material's colour.

### Tinted to the island

**This is `tintLayer`, `GROUND_COLORS`, and the call in `LoadTextures`.**

The island has colours already: Chapter 36's sand, grass, rock and snow, and
section 3's soil and scree. The photographs have their own, the table's
means: the grass is a yellower green, the rock a lighter, greyer stone. Each
is **tinted so that its average is its material's colour**, with a gain per
channel in linear light:

$$ c' = c \times \frac{\text{target}}{\text{mean}} $$

Every texel's red is multiplied by the same number, so the picture's contrast
stays what it was, and only its average moves. For the grass, the mean,
(0.1269, 0.1612, 0.0343) to four places, which the table and the log round to
three, and the target (0.08, 0.15, 0.04) give gains of (0.631, 0.931, 1.168): a
blade's red of 0.20 becomes 0.126, its blue of 0.05 becomes 0.058. The mean is
taken in linear light, decoding each 8-bit sRGB value through a table of all
256, because averages of light are made in linear light; the tinted value is
encoded again, rounded, and clamped at white. Afterwards each photograph
averages to its material's colour within the rounding, which is what makes
section 10 work: from afar, the six colours weighted by the map are what the
photographs average to.

It is a function at file scope, after `uploadLayers`, and logs what it did:

```cpp
// File scope, above the namespace block. Section 6: one photograph's colour, tinted so that its average, in
// linear light, is `target`: every texel's channel times target / mean, which moves the average and keeps the
// contrast; then back to sRGB, rounded, and clamped at white. What it did goes to the log.
static void tintLayer(const char* name, glm::vec3 target, std::vector<uint8_t>& color)
{
    // Every 8-bit sRGB value, decoded once (Chapter 08 section 4).
    std::array<float, 256> linear{};
    for (uint32_t value = 0; value < 256; ++value)
    {
        linear[value] = pf::scene::srgbToLinear(static_cast<float>(value) / 255.0f);
    }
    const size_t texels = color.size() / 4;
    auto mean = [&]() {
        glm::dvec3 sum(0.0);
        for (size_t i = 0; i < texels; ++i)
        {
            sum += glm::dvec3(linear[color[4 * i]], linear[color[4 * i + 1]], linear[color[4 * i + 2]]);
        }
        return glm::vec3(sum / static_cast<double>(texels));
    };

    const glm::vec3 before = mean();
    const glm::vec3 gain   = target / before;
    for (size_t i = 0; i < texels; ++i)
    {
        for (size_t channel = 0; channel < 3; ++channel)
        {
            const float tinted = std::min(linear[color[4 * i + channel]] * gain[static_cast<glm::length_t>(channel)], 1.0f);
            color[4 * i + channel] = static_cast<uint8_t>(pf::scene::linearToSrgb(tinted) * 255.0f + 0.5f);
        }
    }
    const glm::vec3 after = mean();
    Log::info(std::format("{}: mean ({:.3f}, {:.3f}, {:.3f}) tinted to ({:.3f}, {:.3f}, {:.3f})", name, before.r,
                          before.g, before.b, after.r, after.g, after.b).c_str());
}
```

It uses `ColorSpace.h`'s sRGB functions; `std::min` comes from `<algorithm>`,
which `uploadLayers` needed already:

```cpp
#include "PillowFort/Scene/ColorSpace.h"
```

The targets are the six colours of section 3, in the layers' order, at the top
of the namespace after `MAP_FILES`:

```cpp
// Section 6: what each photograph is tinted to average: its material's colour from afar (section 3).
constexpr std::array<glm::vec4, GROUND_LAYERS> GROUND_COLORS{ GROUND_SAND_COLOR, GROUND_GRASS_COLOR, GROUND_SOIL_COLOR,
                                                              GROUND_SCREE_COLOR, GROUND_ROCK_COLOR, GROUND_SNOW_COLOR };
```

and `LoadTextures` tints each colour image once its three files have loaded,
before it joins the others:

```cpp
            tintLayer(GROUND_NAMES[layer], glm::vec3(GROUND_COLORS[layer]), images[0].texels);   // section 6
```

**Normals** need no preparing, if they are OpenGL's, green up the image. A
DirectX normal map has its green the other way; "If something goes wrong" says
what that looks like.

Run it. The log has six lines, one per layer:

```text
Sand: mean (0.345, 0.314, 0.223) tinted to (0.449, 0.401, 0.280)
Grass: mean (0.127, 0.161, 0.034) tinted to (0.080, 0.150, 0.040)
Soil: mean (0.105, 0.056, 0.038) tinted to (0.100, 0.070, 0.040)
Scree: mean (0.198, 0.174, 0.137) tinted to (0.230, 0.220, 0.200)
Rock: mean (0.271, 0.258, 0.195) tinted to (0.220, 0.190, 0.150)
Snow: mean (0.575, 0.580, 0.583) tinted to (0.800, 0.820, 0.850)
```

each mean tinted to its material's colour. From the viewpoint the colours are
section 4's again, no pixel differing from section 4's picture by more than 4
levels of 255. The photographs, averaged by their mip levels, are the island's
colours now. Up close, at **Meadow** and **Shore**, only their hue has moved.

## 7. Bumps without tangents

**This is `readNormal`, `bumped`, the normals in `groundDetail` and `main`, and
a temporary normal check.**

### A tangent from a world axis

A normal map's texel is a direction in the photograph's own frame: x toward
+u, y up the image, z out of the surface (Chapter 15 section 10). To light it,
the shader needs that frame in the world: the tangent T, the direction u grows
in on the ground; the bitangent B, up the image; and the normal N. A mesh
carries its tangents from the importer. The terrain has none, and needs none:
its photographs are laid by projections, and a projection knows which world
direction its u grows in, the rotation's first row, `axis`: from section 6's
u = (x cos θ − z sin θ) / tile, it is (cos θ, 0, −sin θ). So **Projection**
gains that axis, and `topProjection` fills it, after `p.dy`:

```glsl
// Section 6: where a pixel falls in a photograph: its uv, how much the uv changes to the next pixel across
// and down, and (section 7) the world direction in which u grows.
struct Projection
{
    vec2 uv;
    vec2 dx;
    vec2 dy;
    vec3 axis;
};
```

```glsl
    p.axis = vec3(rotation[0].x, 0.0, rotation[1].x);   // u = this . (x, y, z), up to the tile
```

On a slope the axis lies flat, not along the ground, so it is made
perpendicular to N, Chapter 15 section 10's **Gram-Schmidt**: take away the
part of it along N, and normalize. B is then the cross product of N and T
(Chapter 10 section 8's box "Normals and the cross product"):

$$ T = \frac{a - N (N \cdot a)}{\lvert a - N (N \cdot a) \rvert}, \qquad B = N \times T $$

On a slope facing +x, N = (0.6, 0.8, 0) and the axis (1, 0, 0): N · a = 0.6,
so a − 0.6 N = (0.64, −0.48, 0), and normalized, T = (0.8, −0.6, 0), running
down the slope, along the ground. The sign of B is the one to check. On flat
ground N = +Y and T = +X, so B = N × T = −Z. The uv's v grows with z, so −Z is
toward smaller v, up the image, and that is where OpenGL's normal maps point
their green. Got the other way, every bump is lit from the wrong side. `bumped`
and `readNormal` go after `readColor`:

```glsl
// Section 7: Chapter 15 section 10's Gram-Schmidt with a world axis in place of a mesh's tangent: T, the axis
// made perpendicular to N; B, perpendicular to both, pointing up the image; and n from that space to the
// world's.
vec3 bumped(vec3 N, vec3 axis, vec3 n)
{
    vec3 T = normalize(axis - N * dot(N, axis));
    vec3 B = cross(N, T);
    return normalize(T * n.x + B * n.y + N * n.z);
}
```

### The normals, blended

A layer's normal is read with the same projection as its colour, through the
same derivatives, and bent into the world by `bumped`:

```glsl
// Section 7: one read of a layer's normal, in the tangent space of its projection: x along u, y up the image,
// z out of the ground (OpenGL's convention, green up).
vec3 readNormal(sampler2DArray normals, uint layer, Projection p)
{
    return textureGrad(normals, vec3(p.uv, float(layer)), p.dx, p.dy).xyz * 2.0 - 1.0;
}
```

Where two layers show, their world normals are mixed by the same shares as
their colours, and normalized. `groundDetail` now returns both, so it returns
a struct, declared above it:

```glsl
// Section 6: what the photographs show at a pixel: its albedo, and (section 7) its normal.
struct GroundSurface
{
    vec3 albedo;
    vec3 normal;
};
```

and takes the normals' image and the ground's normal N:

```glsl
GroundSurface groundDetail(sampler2DArray colors, sampler2DArray normals, float w[6], vec3 position, vec3 N,
                           vec3 dpx, vec3 dpy)
```

Its first loop and `b` stay as they are; its second loop now adds up the
normals too, and the function returns the struct:

```glsl
    // Section 6: the colors by their shares. Section 7: and the normals, read only where they show.
    GroundSurface surface = GroundSurface(vec3(0.0), vec3(0.0));
    for (uint i = 0u; i < 6u; ++i)
    {
        if (b[i] > MIN_WEIGHT)
        {
            surface.albedo += b[i] * color[i].rgb;
            Projection p = topProjection(i, position, dpx, dpy);
            surface.normal += b[i] * bumped(N, p.axis, readNormal(normals, i, p));
        }
    }
    surface.normal = normalize(surface.normal);
    return surface;
```

In `main`, on land, the light uses the bumped normal, mixed in by `near` like
the colour. The **shadow** keeps the ground's own normal: `sunShadow`'s bias
leans the lookup along N (Chapter 17 section 7), and a bumpy N would scatter it
into acne. From the `albedo` line to the branch's last line, section 6's
`if (near > 0.0)` block and `color = albedo * lightAt(N, sunLit);` among them,
become:

```glsl
            vec3  albedo    = groundFarColor(w) * variation;
            vec3  shading   = N;

            // Section 6: the photographs, while any of them shows; section 7: their normals.
            if (near > 0.0)
            {
                GroundSurface surface = groundDetail(groundColors, groundNormals, w, worldPosition, N, dpx, dpy);
                albedo  = mix(albedo, surface.albedo * variation, near);
                shading = normalize(mix(N, surface.normal, near));
            }
            color = albedo * lightAt(shading, sunLit);
```

Run it. At **Shore** the ripples stand out of the sand, lit on the side facing
the sun; at **Stream** the soil is clods and the grass a tangle; at **Cliff**
the scree's stones are stones.

### The normal check

Whether a normal map is lit the right way round is hard to judge on a
photograph of grass. A temporary edit replaces every normal read with a shape
whose answer is known: a **dome** in every tile, its normal leaning out from
the tile's middle, (2 f.x, −2 f.y, 1), normalized, with f the position in the
tile from −0.5 to 0.5 (−y, because y is up the image and f.y grows down it).
It goes through exactly the same projection, axis and `bumped` as a
photograph. At the top of `readNormal`:

```glsl
    vec2 f = fract(p.uv) - 0.5;   // the normal check: a dome in every tile
    return normalize(vec3(2.0 * f.x, -2.0 * f.y, 1.0));
```

and, so that all that shows is light, a flat grey at the top of `readColor`:

```glsl
    return vec4(0.5);   // the normal check: flat grey
```

Build, press **Meadow**, and look straight down at the grass: hold the right
mouse button on the scene and drag down. The view turns 0.17 degrees a pixel
and stops at 89 degrees, just short of straight down, so from Meadow's 12
degrees below the horizon it is about 450 pixels, in two drags if the pointer
reaches the window's edge first, and more does no harm. A field of grey domes
in rows turned by the grass's 61 degrees, every one lit on the side facing the
sun and dark on the other. Take the three lines out again.

## 8. Where two layers meet

**This is `stretchHeight`, `HEIGHT_DEPTH` and `heightBlend`, and one line in
`groundDetail`.**

### The problem

The map's weights change over 32 m cells, smoothly. Where a beach meets the
grass, sand's weight runs from 1 to 0 as the ground rises from 2.5 m to 9 m,
on a coast that climbs that 6.5 m in about 250 m: a cross-fade **a few hundred
metres wide**, in which a photograph of sand is printed at half strength over
one of grass. Real ground does not blend like that. It meets: the grass grows
in clumps out of the sand, sand drifts into the low places between them, and
stones stick up out of the soil.

### The heights, made comparable

The height maps decide who shows where two layers meet, so they must be
comparable, and as published they are not: the six were made separately and
spread differently. The sand's heights have a mean of 0.53, and their 1st and
99th percentiles are 0.24 and 0.74, a span of 0.50; the snow's lie between
0.46 and 0.82. One layer whose heights all sit high would win every border.
So each is **stretched** so that its own 1st to 99th percentiles span 1, and
centred on its mean at 0.5:

$$ h' = 0.5 + \frac{h - \bar h}{h_{99} - h_{1}} $$

clamped to 0 and 1. The sand's 0.74 becomes 0.5 + (0.74 − 0.53) / 0.50 = 0.92.
The percentiles come from a histogram of the 256 values, and the stretched
height goes into the colour's alpha, as section 5 planned. A function at file
scope, after `tintLayer`:

```cpp
// File scope, above the namespace block. Section 8: one photograph's height, stretched so that its own 1st to
// 99th percentiles span 1 and centred on its mean at 0.5, written into the colour's alpha. What it did goes
// to the log.
static void stretchHeight(const char* name, const std::vector<uint8_t>& height, std::vector<uint8_t>& color)
{
    // The percentiles, from a histogram of the height's 256 values (grey, so red is enough).
    const size_t texels = height.size() / 4;
    std::array<size_t, 256> histogram{};
    double sum = 0.0;
    for (size_t i = 0; i < texels; ++i)
    {
        ++histogram[height[4 * i]];
        sum += height[4 * i];
    }
    auto percentile = [&](double fraction) {
        size_t seen = 0;
        for (uint32_t value = 0; value < 256; ++value)
        {
            seen += histogram[value];
            if (static_cast<double>(seen) >= fraction * static_cast<double>(texels)) { return static_cast<float>(value); }
        }
        return 255.0f;
    };
    const float low    = percentile(0.01);
    const float high   = percentile(0.99);
    const float middle = static_cast<float>(sum / static_cast<double>(texels));
    const float span   = std::max(high - low, 1.0f);
    for (size_t i = 0; i < texels; ++i)
    {
        const float stretched = std::clamp(0.5f + (static_cast<float>(height[4 * i]) - middle) / span, 0.0f, 1.0f);
        color[4 * i + 3] = static_cast<uint8_t>(stretched * 255.0f + 0.5f);
    }
    Log::info(std::format("{}: height {:.2f} to {:.2f}, mean {:.2f}, stretched", name, low / 255.0f, high / 255.0f,
                          middle / 255.0f).c_str());
}
```

`LoadTextures` calls it after the tint:

```cpp
            stretchHeight(GROUND_NAMES[layer], images[2].texels, images[0].texels);              // section 8
```

and the log gains six more lines, each after its layer's tint line:

```text
Sand: height 0.24 to 0.74, mean 0.53, stretched
Grass: height 0.10 to 0.72, mean 0.34, stretched
Soil: height 0.33 to 0.78, mean 0.57, stretched
Scree: height 0.14 to 0.66, mean 0.40, stretched
Rock: height 0.22 to 0.89, mean 0.53, stretched
Snow: height 0.46 to 0.82, mean 0.65, stretched
```

### Blending by height

> **Jump:** so far a weight has said how much of a material shows. Here it
> becomes a *head start* in a contest that the height maps decide at every
> pixel. Keep in mind what the weights still guarantee: where one layer's weight
> is 1, it shows alone, and the shares a pixel shows always add up to 1.

Each layer's **key** is its height at this pixel, centred on 0, plus its
weight. The highest key wins, and the layers within `HEIGHT_DEPTH` of it
share the pixel, each by how far above that line it stands:

$$ k_i = (h_i - 0.5) + w_i, \qquad b_i = \max(k_i - \max_j k_j + d,\ 0), \qquad \text{shares} = \frac{b_i}{\sum_j b_j} $$

with d = 0.2. The sum is at least d, the highest layer's own share, so it is
never 0. Two layers at a pixel where the sand's height is 0.2 and the rock's
0.8: with weights 0.5 and 0.5, the keys are 0.2 and 0.8, the line is at 0.6,
the sand's key is under it, and the rock shows alone: its tops stand out of
the sand. With weights 0.8 and 0.2, the keys are 0.5 and 0.5, both 0.2 above
the line, and they share it half and half. As the sand's weight rises across
the border, the rock sinks into it, its high points last. `HEIGHT_DEPTH` is a
constant, after `MIN_WEIGHT`:

```glsl
// Section 8: how far below the highest layer another may stand and still show, in heights of a photograph.
const float HEIGHT_DEPTH = 0.2;
```

and `heightBlend` is a function above `GroundSurface`:

```glsl
// Section 8: where two materials meet, the one standing higher in its photograph shows. A layer's key is its
// height, centred on 0, plus its weight; the layers within HEIGHT_DEPTH of the highest key share the pixel,
// each by how far above that line it stands. `b` comes in as the weights and leaves as the shares.
void heightBlend(vec4 color[6], inout float b[6])
{
    float key[6];
    float highest = -1.0e9;
    for (uint i = 0u; i < 6u; ++i)
    {
        key[i]  = b[i] > MIN_WEIGHT ? (color[i].a - 0.5) + b[i] : -1.0e9;
        highest = max(highest, key[i]);
    }
    float sum = 0.0;
    for (uint i = 0u; i < 6u; ++i)
    {
        b[i] = max(key[i] - highest + HEIGHT_DEPTH, 0.0);
        sum += b[i];
    }
    for (uint i = 0u; i < 6u; ++i)
    {
        b[i] /= sum;   // at least HEIGHT_DEPTH: the highest layer's own share
    }
}
```

In `groundDetail`, between the two loops, the comment above `float b[6] = w;`
changes, and the call follows that line:

```glsl
    // Section 8: the shares the photographs show, from their heights.
    float b[6] = w;
    heightBlend(color, b);
```

Normals are now read only for layers that show, usually one, where the
cross-fade read every layer with weight. Run it: **Meadow**, where the rock
comes down to the grass in clumps and the grass reaches up between its stones;
**Shore**, the grass in tufts through the sand; **Stream**, stones of the soil
standing out of the grass along its edge.

## Checkpoint

Real ground under the camera. **Meadow**, **Shore** and **Stream** show relief
in the light and borders made of clumps and stones, not a cross-fade; with
section 7's temporary edit, every dome is lit on its sun side. From the
viewpoint the picture is close to Part 1's, the ground's mean colour within a
level of 255 of section 4's, though single pixels move where bumps catch the
light and the height blend picks one layer over another; section 10 makes it
section 4's exactly. Untick **Detail up close** to compare.

`groundDetail` is complete but for rock, which section 9 reads from three
sides:

```glsl
GroundSurface groundDetail(sampler2DArray colors, sampler2DArray normals, float w[6], vec3 position, vec3 N,
                           vec3 dpx, vec3 dpy)
{
    // Section 6: every material with a weight, its color read once.
    vec4 color[6];
    for (uint i = 0u; i < 6u; ++i)
    {
        color[i] = vec4(0.0);
        if (w[i] > MIN_WEIGHT)
        {
            color[i] = readColor(colors, i, topProjection(i, position, dpx, dpy));
        }
    }

    // Section 8: the shares the photographs show, from their heights.
    float b[6] = w;
    heightBlend(color, b);

    // Section 6: the colors by their shares. Section 7: and the normals, read only where they show.
    GroundSurface surface = GroundSurface(vec3(0.0), vec3(0.0));
    for (uint i = 0u; i < 6u; ++i)
    {
        if (b[i] > MIN_WEIGHT)
        {
            surface.albedo += b[i] * color[i].rgb;
            Projection p = topProjection(i, position, dpx, dpy);
            surface.normal += b[i] * bumped(N, p.axis, readNormal(normals, i, p));
        }
    }
    surface.normal = normalize(surface.normal);
    return surface;
}
```

and `main`, as it stands, which Part 3 changes in one line (section 10) and
one block after the haze (section 11). Its comments are the ones it keeps: a
section's snippet shows the comment it had when that section was written, and
this listing the comment the lines end with, so the two may word one line
differently:

```glsl
void main()
{
    vec3  toEye = frame.cameraPosition.xyz - worldPosition;
    float range = length(toEye);
    vec3  V     = toEye / range;

    // Chapter 38 section 2: what the ground is made of here. The push constant's flag is the same for every
    // pixel, so the map's implicit derivatives are fine inside the test.
    bool  ground = (terrain.flags & TERRAIN_GROUND) != 0u;
    float w[6];
    if (ground)
    {
        groundWeights(groundMap, groundMapUv(worldPosition.xz, terrain.heightmap.x), w);
    }

    // Chapter 38 section 3: how far the ground moves from this pixel to the next across and down, and so how
    // much ground one pixel covers, in metres. Section 6: taken here, before any branch, while every pixel of
    // the quad still runs, so that every read below may sit in a branch.
    vec3  dpx       = dFdx(worldPosition);
    vec3  dpy       = dFdy(worldPosition);
    float footprint = max(length(dpx), length(dpy));

    // Section 6: how much of the photographs shows here: all of it, while the switch is on.
    float near = (terrain.flags & TERRAIN_GROUND_DETAIL) != 0u ? 1.0 : 0.0;

    // Chapter 36 section 4: the ground, lit; its section 10: or water, where the ground is below sea level.
    // Chapter 37 section 8: the sun's light in the objects' shadows (Chapter 17), out to the shadows' distance.
    float viewDepth = -(frame.view * vec4(worldPosition, 1.0)).z;
    vec3  color;
    if (groundHeight < 0.0)
    {
        // Chapter 38 section 3: under shallow water, what the map says is there; section 6: up close, the
        // sand's photograph. Deeper, Chapter 36's sand, which no one can see by then.
        vec3 seaFloor = groundAlbedo(0.0, 1.0);
        if (ground && -groundHeight < FLOOR_DEPTH)
        {
            float variation = groundVariation(worldPosition.xz, footprint);
            seaFloor = groundFarColor(w) * variation;
            if (near > 0.0)
            {
                vec3 sand = readColor(groundColors, SAND, topProjection(SAND, worldPosition, dpx, dpy)).rgb;
                seaFloor  = mix(seaFloor, sand * variation, near);
            }
        }
        color = waterColor(-groundHeight, V, sunShadow(worldPosition, vec3(0.0, 1.0, 0.0), viewDepth), seaFloor);
    }
    else
    {
        vec3  N      = normalize(vertexNormal);
        float sunLit = sunShadow(worldPosition, N, viewDepth);   // the ground's own N: a bumpy one gives acne
        if (!ground)
        {
            color = groundAlbedo(groundHeight, N.y) * lightAt(N, sunLit);
        }
        else
        {
            // Chapter 38 section 3: the map's weights, rock wherever this pixel is steep, and the color from afar.
            addSteepRock(w, N.y);
            float variation = groundVariation(worldPosition.xz, footprint);
            vec3  albedo    = groundFarColor(w) * variation;
            vec3  shading   = N;

            // Section 6: the photographs, while any of them shows; section 7: their normals.
            if (near > 0.0)
            {
                GroundSurface surface = groundDetail(groundColors, groundNormals, w, worldPosition, N, dpx, dpy);
                albedo  = mix(albedo, surface.albedo * variation, near);
                shading = normalize(mix(N, surface.normal, near));
            }
            color = albedo * lightAt(shading, sunLit);
        }
    }

    // Chapter 36 section 11: haze. Far ground fades into the sky behind it: the fraction left after `range`
    // metres is exp(-range / hazeDistance), as Chapter 30's sea fades (its section 10), at tens of kilometres.
    // The debug views below come after it, so their colors reach the horizon unhazed.
    color = hazed(color, V, range, (terrain.flags & TERRAIN_SKY) != 0u, terrain.sky);

    // Chapter 38 section 2: the map's weights on the land, as false colors.
    if ((terrain.flags & TERRAIN_SHOW_MATERIALS) != 0u && ground && groundHeight >= 0.0)
    {
        color = groundFalseColor(w);
    }

    // Chapter 37 section 6: the forest's density, as dark green.
    if ((terrain.flags & TERRAIN_SHOW_FOREST) != 0u)
    {
        color = mix(color, vec3(0.0, 0.3, 0.0), 0.8 * forest);
    }

    // Section 2: the debug view, a color per ring.
    if ((terrain.flags & TERRAIN_SHOW_RINGS) != 0u)
    {
        color = mix(color, RING_COLORS[ring % 6u] * 0.5, 0.6);
    }
    // Section 1: dark lines along every cell edge, about a pixel wide whatever the cell's size on screen:
    // fwidth is how far cellPosition changes across one pixel.
    if ((terrain.flags & TERRAIN_SHOW_CELLS) != 0u)
    {
        vec2  toEdge = abs(fract(cellPosition + 0.5) - 0.5) / max(fwidth(cellPosition), vec2(1e-6));
        float line   = 1.0 - clamp(min(toEdge.x, toEdge.y), 0.0, 1.0);
        color *= 1.0 - 0.75 * line;
    }
    outColor = vec4(color, 1.0);
}
```

---

# Part 3 — Cliffs and distance (sections 9-11)

Two places still look wrong: cliffs, where a photograph laid from above runs
down the face in streaks, and the distance, where the photographs show only
their own repeat. Part 3 fixes both, and counts the texture reads they cost.

## 9. Rock from three sides

**This is `SIDE_MIN`, `sideProjection`, `rockProjection`, `triplanarWeights`,
`rockColor` and `rockNormal`, and rock's two lines in `groundDetail`.**

### Stretching

A photograph laid from above covers a slope by its shadow on the ground: a
slope at angle θ is 1 / cos θ times as long as its shadow, so the photograph
is stretched by that along the slope. At 45 degrees that is 1.41, and still
reads as rock; at 75 it is 3.9, and every pebble becomes a streak running down
the face. Rock is the material on steep ground by construction, from the map
and from `addSteepRock`, so it is the one that needs a cure. Scree lies on
aprons of 30 to 40 degrees, stretched 1.15 to 1.3, and keeps its top
projection.

### Three projections

> **Jump:** a photograph has been laid one way, from above. Rock is laid three
> ways at once, from above and from the two horizontal axes, and the three are
> blended by how squarely the surface faces each. Keep in mind that each of
> the three is just another `Projection`, with its own uv, derivatives and
> axis, read and bent exactly as section 7's.

**Triplanar** mapping lays the photograph three times, each straight onto one
plane of the world: from above, as before; from the side along x, onto the
z-y plane; from the side along z, onto the x-y plane. A face looking mostly
along x shows the x side's, square on, unstretched; flat ground the top's.
The three are blended by how squarely the normal N faces each axis, its
components to the fourth power, so the nearest axis wins quickly and the
blend zones stay narrow:

$$ w = \frac{(n_x^4,\ n_y^4,\ n_z^4)}{n_x^4 + n_y^4 + n_z^4} $$

On a slope facing +x, N = (0.6, 0.8, 0): 0.6⁴ = 0.13 and 0.8⁴ = 0.41, so the x
side shows 0.24 and the top 0.76. A projection under `SIDE_MIN`, 2 %, is not
read at all, and the others share what it would have had: on flat ground only
the top is read, and the cost is a single projection's. Skipping a read on a
branch like that is legal only because every read passes its own derivatives
(section 6).

The side projections must not mirror the photograph, nor lay it on its side.
Seen from outside, a face looking along +x has −z to its right, and one looking
along −x has +z; so on the x side u runs along −z on the first and +z on the
second, u = sx · (−z), with sx the sign of N's x (taken as +1 at exactly 0),
and v runs down the face, v = −y. The direction u grows in, the axis, is
h = (0, 0, −sx). The z side is the same turned a quarter: u = sz · x,
h = (sz, 0, 0). Both are one function, whose u is the position measured along
h. Check one face: N = (1, 0, 0), so sx = 1 and T = h = (0, 0, −1), already
perpendicular to N; B = N × T = (0 · (−1) − 0 · 0, 0 · 0 − 1 · (−1),
1 · 0 − 0 · 0) = (0, 1, 0), +Y, up the image, as section 7's sign check needs.
The same holds on every face. `SIDE_MIN` is a constant, after `HEIGHT_DEPTH`;
the five functions that follow it go together after `bumped` and `readNormal`,
which they call, and above `heightBlend`:

```glsl
// Section 9: a projection that would show less than this share of the rock is not read at all.
const float SIDE_MIN = 0.02;
```

```glsl
// Section 9: rock on a side face, the photograph standing upright on it: u along `h`, a level direction
// across the face, and v down it.
Projection sideProjection(vec3 position, vec3 dpx, vec3 dpy, vec3 h)
{
    float tile = GROUND_TILE[ROCK];
    Projection p;
    p.uv   = vec2(dot(position, h), -position.y) / tile;
    p.dx   = vec2(dot(dpx, h), -dpx.y) / tile;
    p.dy   = vec2(dot(dpy, h), -dpy.y) / tile;
    p.axis = h;
    return p;
}
```

`rockProjection` picks one of the three by number, so that rock's colour and
normal can loop over them:

```glsl
// Section 9: rock's three projections, by `side`: 0 from the x side, 1 from above, 2 from the z side. Seen
// from outside, a face looking along +x has -z to its right, and one looking along -x has +z; so the x side's
// u runs along -z times the sign of N.x, and the z side's along +x times the sign of N.z. No face is mirrored.
Projection rockProjection(uint side, vec3 position, vec3 N, vec3 dpx, vec3 dpy)
{
    if (side == 1u)
    {
        return topProjection(ROCK, position, dpx, dpy);
    }
    float sx = N.x < 0.0 ? -1.0 : 1.0;
    float sz = N.z < 0.0 ? -1.0 : 1.0;
    vec3  h  = side == 0u ? vec3(0.0, 0.0, -sx) : vec3(sz, 0.0, 0.0);
    return sideProjection(position, dpx, dpy, h);
}
```

```glsl
// Section 9: how much of each projection shows at N: |n| to the fourth, so the nearest axis wins quickly. A
// share under SIDE_MIN is not read at all, and the others share what it would have had.
vec3 triplanarWeights(vec3 N)
{
    vec3 weights = N * N * N * N;
    weights /= weights.x + weights.y + weights.z;
    weights *= step(SIDE_MIN, weights);
    return weights / (weights.x + weights.y + weights.z);
}
```

Rock's colour and normal are the three, each read and bent as section 7's, by
their weights:

```glsl
// Section 9: rock's color, from its three projections, blended by triplanarWeights.
vec4 rockColor(sampler2DArray colors, vec3 position, vec3 N, vec3 dpx, vec3 dpy)
{
    vec3 weights = triplanarWeights(N);
    vec4 color   = vec4(0.0);
    for (uint side = 0u; side < 3u; ++side)
    {
        if (weights[side] > 0.0)
        {
            color += weights[side] * readColor(colors, ROCK, rockProjection(side, position, N, dpx, dpy));
        }
    }
    return color;
}
```

```glsl
// Section 9: and its normal, each projection's bent into the world through its own axis (section 7).
vec3 rockNormal(sampler2DArray normals, vec3 position, vec3 N, vec3 dpx, vec3 dpy)
{
    vec3 weights = triplanarWeights(N);
    vec3 normal  = vec3(0.0);
    for (uint side = 0u; side < 3u; ++side)
    {
        if (weights[side] > 0.0)
        {
            Projection p = rockProjection(side, position, N, dpx, dpy);
            normal += weights[side] * bumped(N, p.axis, readNormal(normals, ROCK, p));
        }
    }
    return normalize(normal);
}
```

In `groundDetail`'s first loop, rock's colour is read three ways, in place of
the one `color[i] =` line:

```glsl
            color[i] = i == ROCK ? rockColor(colors, position, N, dpx, dpy)
                                 : readColor(colors, i, topProjection(i, position, dpx, dpy));
```

and in its second loop, rock's normal, in place of the two lines after
`surface.albedo += ...`:

```glsl
            if (i == ROCK)
            {
                surface.normal += b[i] * rockNormal(normals, position, N, dpx, dpy);
            }
            else
            {
                Projection p = topProjection(i, position, dpx, dpy);
                surface.normal += b[i] * bumped(N, p.axis, readNormal(normals, i, p));
            }
```

The height blend needs nothing new: the rock's height is the alpha of its
blended colour.

Run it, and press **Cliff**: a face of 77 degrees rises 230 m in front of you,
the rock's grain at its real size all the way up, with no streaks running down
it; you stand on the scree at its foot. With section 7's temporary edit in
again, the domes on the face are not drawn out down the slope, and each is lit
like its neighbours. Where a face turns between two axes, two projections share
it and their domes overlap in a lattice; at the foot, scree and rock take the
pixels by height, each with its own domes, in patches. Both are the blends at
work, not faults.

## 10. The far island

**This is `DETAIL_NEAR`, `DETAIL_FAR` and the fade.**

### Repetition

A pixel covers about 1.07 mm for every metre of distance in a window 1,080
pixels tall. At 150 m that is 16 cm, and rock's 2.4 m tile is 15 pixels
across; at 300 m, 7.5 pixels. Past a few hundred metres every photograph is
its tile, over and over, a fine grid on the ground that the eye finds at once,
and its reads cost the same as near ones. Up close is where the photographs
earn their reads.

### The fade

So the photographs show fully up to `DETAIL_NEAR`, 150 m, and fade into the
far colour by `DETAIL_FAR`, 300 m; past 300 m nothing is read at all. In
`Terrain.frag`, above `RING_COLORS`:

```glsl
// Chapter 38 section 10: the photographs up to DETAIL_NEAR metres away, fading into the far color by DETAIL_FAR.
const float DETAIL_NEAR = 150.0;
const float DETAIL_FAR  = 300.0;
```

and `near` becomes the fade, by `range`, the distance from the camera that
`main` works out first (Chapter 36):

```glsl
    // Section 6: how much of the photographs shows here, while the switch is on; section 10: all of it up to
    // DETAIL_NEAR, fading out by DETAIL_FAR.
    float near = (terrain.flags & TERRAIN_GROUND_DETAIL) != 0u ? 1.0 - smoothstep(DETAIL_NEAR, DETAIL_FAR, range) : 0.0;
```

> **Jump:** what the photographs fade into is the far colour of section 3,
> read through the map's mip levels. Keep in mind section 1's argument: each
> mip level of the map is an average of the weights below it, so a far pixel's
> weights are the true shares of all the ground it covers, and its far colour
> is those shares times the six colours.

What it fades into is an **island-wide colour map** that is computed, not
stored: the map's own mip levels, times the six colours, times the variation.
No file has to be kept in step with the photographs, and swapping a
photograph changes nothing far away, because section 6's tint makes every one
average to its colour.

The join **approximates** a seamless one; it is not exact. The height blend is
not linear (the shares a pixel shows are not its weights), the photographs'
smallest mip levels are rounded at every level, and the normals change the
light a little. The Exit check measures it, at the Meadow, detail on against
off: over all the ground 100 to 300 m away the mean colour moves by at most
1.2 % of the mean, and down the screen through both bands the ground's average
brightness changes from one row to the next no more than it does with the
photographs off, where the variation's patches change it: no line.

From the viewpoint, 878 m above the nearest ground, no pixel is within 300 m,
and **Detail up close** on and off are the same picture, byte for byte: the
far view is section 3's, whatever happens up close.

Run it. **Meadow**, then fly low toward the hills: no line where the
photographs end, and no grid. **Back to the viewpoint**: the picture of section
3.

## 11. What it costs

**This is `groundReads` and `readsColor`, the reads' view in `main`, and its
key on the panel; then the numbers that keep the terrain inside a budget.**

### Counting reads

A ground pixel's cost is mostly its texture reads. **Show reads**, the last of
section 2's switches, colours each land and water pixel by how many of this
chapter's reads it made: green up to 3, yellow 4 to 6, orange 7 to 10, red 11
or more. A counter, `groundReads`, is a global of the include, among the
constants after `SIDE_MIN` and above `groundMapUv`, the first function:
`groundWeights`, below, counts into it, and a name is declared before its
first use. The heightmap, the sky's cubes and the shadow map are not counted:

```glsl
// Section 11: how many reads of the ground's images this pixel has made.
uint groundReads = 0u;
```

Each read adds to it where it happens: in `groundWeights`, after its two
`texture()` reads,

```glsl
    groundReads += 2u;                               // section 11
```

and the same line, adding one, at the top of `readColor` and of `readNormal`,
before each one's `textureGrad`:

```glsl
    groundReads += 1u;   // section 11
```

The four colours go in `HorizonTypes.h`, after the six colours, because the
panel shows them too:

```c
/* Chapter 38 section 11: Show reads' colours, linear, by how many ground reads a pixel made. */
#define READS_GREEN   vec4(0.10f, 0.70f, 0.10f, 1.0f)   /* up to 3 */
#define READS_YELLOW  vec4(0.90f, 0.80f, 0.10f, 1.0f)   /* 4 to 6 */
#define READS_ORANGE  vec4(1.00f, 0.45f, 0.05f, 1.0f)   /* 7 to 10 */
#define READS_RED     vec4(0.90f, 0.05f, 0.05f, 1.0f)   /* 11 or more */
```

and the function that turns a count into one of them goes last in the include,
above the guard's `#endif`:

```glsl
// Section 11: a pixel's ground reads as a color (HorizonTypes.h): green up to 3, yellow 4 to 6, orange 7 to
// 10, red 11 or more.
vec3 readsColor(uint reads)
{
    return reads <= 3u  ? READS_GREEN.rgb
         : reads <= 6u  ? READS_YELLOW.rgb
         : reads <= 10u ? READS_ORANGE.rgb
                        : READS_RED.rgb;
}
```

In `main`, after the false colours, the view mixes the band's colour half and
half into the picture, so that the scene still shows through and a cliff keeps
its shape; the false colours stay flat, so that a probe reads them exactly:

```glsl
    if ((terrain.flags & TERRAIN_SHOW_READS) != 0u)
    {
        color = mix(color, readsColor(groundReads), 0.5);
    }
```

On the panel, while **Show reads** is on, a line under the switches says what
the colours mean, each count in its colour:

```cpp
    // Section 11: while Show reads is on, what its colours mean.
    if (m_terrainSettings.showReads)
    {
        constexpr std::array<glm::vec4, 4>   bands{ READS_GREEN, READS_YELLOW, READS_ORANGE, READS_RED };
        constexpr std::array<const char*, 4> counts{ "0-3", "4-6", "7-10", "11+" };
        ImGui::TextUnformatted("Reads");
        for (size_t band = 0; band < bands.size(); ++band)
        {
            const glm::vec3 shown = scene::linearToSrgb(glm::vec3(bands[band]));   // ImGui's colors are sRGB
            ImGui::SameLine();
            ImGui::TextColored(ImVec4(shown.r, shown.g, shown.b, 1.0f), "%s", counts[band]);
        }
    }
```

What a pixel reads, by where it is:

| Pixel | Map | Colour | Normal | Total |
| --- | --- | --- | --- | --- |
| **Ground materials** off | 0 | 0 | 0 | 0 |
| Deep water, land past 300 m, or **Detail up close** off | 2 | 0 | 0 | 2 |
| Shallows within 300 m | 2 | 1 | 0 | 3 |
| Land within 300 m, one material (four-fifths of the land is grass) | 2 | 1 | 1 | 4 |
| A border of two materials | 2 | 2 | 1-2 | 5-6 |
| A cliff: rock from two or three sides, and one other material | 2 | 3-4 | 1-4 | 6-10 |
| The worst case: six materials, rock from three sides, all showing | 2 | 8 | 8 | 18 |

The worst case needs six weights above 1/255 at one pixel, which the map almost
never has. In practice: from the viewpoint every pixel reads two, green; over
grass within 300 m, most of the land, four, yellow; at **Meadow** some orange
and a few red pixels, along the rock's clumps; and at **Cliff** yellow and
orange, none red (the Exit check counts it). The height blend leaves one layer
showing at most pixels, so the other layers' normals are not read.

### What it costs in time

**Times** (Chapter 37 section 9) has the terrain's time already, between
timestamps 2 and 3; nothing new is timed. To see what this chapter costs, read
it with **Ground materials** on and off, and with **Detail up close** off, in
the same view. On lavapipe, which runs on the CPU, compare only with **Draw
objects** off, as Chapter 37 section 9 found, and take its milliseconds as
proportion only: a CPU's time says little about a GPU's, so from lavapipe
**Show reads** is the only measure of cost that carries over.

**A budget**, so that a timing can pass or fail, against the target Chapter 37
section 9 sets (the RTX 4060 Laptop at 1920 x 1080, 4x MSAA; the Radeon 890M is
measured and reported, not held to it): at most **+0.4 ms**, with the Full
preset and the sun sky, in the worst of Chapter 37's **Wood**, **Village** and
**Edge**, where half the window or more is ground within 300 m: about a million
pixels, most of them grass at four reads. It is a target, not a measurement. If
the budget is over, cut in this order, measuring after each:

1. **Anisotropy**, 16x, then 8x, then 4x. It needs a sampler of the demo's
   own, since `createMaterialSampler` fixes 16x.
2. **The detail range**: `DETAIL_NEAR` and `DETAIL_FAR` from 150 and 300 m to
   100 and 200 m, then 75 and 150 m.
3. **Triplanar off**: rock from above only.
4. **Normals only within 64 m.**
5. **The terrain drawn after the objects**, so that the ground hidden behind
   trees and houses is not shaded. That reorders Chapter 37's `Record` and its
   timers, so only if the timings show the hidden ground matters.

### What the next chapters read

The map is built to be read by more than the terrain. Far Cry 5's terrain data
also feeds its trees, grass and rocks, and Horizon Zero Dawn places its plants
by rules over world maps such as humidity and distance to a river. Chapter 39's
plants read the weights at each cell, in a compute pass over set 1; the
chapters after it read the map too:

| Reader | What it reads | How | Chapter |
| --- | --- | --- | --- |
| Forests | Chapter 37's `forestDensity`, perhaps times (1 − sand − scree − rock − snow), changed with the mesh trees | set 1, binding 0 and 1 | 40 |
| Grass | the grass weight, for its density; and its far fade landing on `groundFarColor(w) × groundVariation`, what the terrain draws past 300 m | set 1 | 41 |
| The scene graph | `WeightsAt` and `HeightAt`, on the CPU | `Terrain::Materials()` | later |
| The coast | the sand weight, the floor's colour and depth, and a distance to the shore of its own at binding 4 | set 1 | later |

The forest is left alone here. Measured over the whole map on a 16 m grid, each
point's six weights (`WeightsAt`'s bilinear sample) weighted by Chapter 37's
forest density there, the forest lies 95.4 % on grass and soil, 4.1 % on
scree, 0.4 % on rock, 0.1 % on sand and none on snow. So there is nothing to
correct, and changing it would move every number Chapter 37 measured.

## Checkpoint

The finished chapter. From the viewpoint, the island painted by its map, as
in Part 1, and the same picture byte for byte with **Detail up close** off. At
any of the five views, the photographs under the camera, lit through their
normals and meeting in clumps; at **Cliff**, rock laid from three sides; and
from **Meadow**, the photographs fading into the far colour with no line.
**Show reads** says what each pixel paid. Every terrain pixel is now the
outline the chapter began with, every part written; the frame around it is
Chapter 37's, unchanged. The Exit check below walks through all of it.

---

## If something goes wrong

| Symptom | Cause |
| --- | --- |
| The log says "No material map", and the ground is Chapter 37's | `IslandMaterials0.png` or `IslandMaterials1.png` is missing beside the executable, or is a Git LFS pointer file, a few hundred bytes of text: fetch LFS (`git lfs pull`), then build so `Assets/` is copied again (section 2) |
| Streams in the sea, beaches on the hills, the island painted on a different island | The maps and `Island.png` come from different runs: on another Python, a rerun's map fits a rerun's island. Use all three files from one run (the Appendix) |
| The colours of the map look shifted, or a weight is wrong in one region only | The map was opened and saved in an image editor, which may drop or change channels. Never re-save it; run the script again (section 1) |
| A validation error at pipeline creation naming set 1 and the fragment stage | A binding of the island's set is not visible to the fragment shader: every binding takes `ISLAND_STAGES` (section 2) |
| Streams and scree shimmer and crawl from the viewpoint as you turn | `groundVariation`'s octaves are not faded by the footprint, or the footprint is taken inside a branch (section 3) |
| The log says "No ground textures", and the ground is flat up close | One of the eighteen files is missing, of another size, or a Git LFS pointer file: the warning names it; fetch LFS (`git lfs pull`) and build again (section 5) |
| Up close the ground is much brighter or darker than from afar, or the wrong hue, with a line at 150-300 m | The tint is not applied (section 6), or the colour image is `_UNORM`, so the photographs are read as if linear (section 5) |
| Every bump lit from below, ripples looking like grooves | A DirectX normal map, green down the image: take the GL one, or negate green when loading (section 5); or B's sign is wrong in `bumped` (section 7) |
| Seams of a different blur along the borders of materials, on some GPUs only | A read with `texture()` inside a branch: every detail read must be `textureGrad` with the derivatives from the top of `main` (section 6) |
| Speckled light, sparkling acne in the shade | `sunShadow` is given the bumped normal; it takes the ground's own N (section 7) |
| Cliff faces mirrored, or lit from inside | A side projection's sign: u must run along sx · (−z) on the x side and sz · x on the z side (section 9) |

## Exit check

Run the finished demo in a 1280 x 720 window, as the harness runs it, with the
sky on and **Ground** open. Pixel values and shares are the reference run's, on
lavapipe, read from screenshots with `pf.py probe` (`Tests/TutorialHarness`'s
README, "Commands", shows how: `python3 pf.py probe shot.png 640,360` prints the
pixel at 640, 360); any colour picker does for a single pixel, and your GPU's
will differ a little. Counts are over the picture outside the windows, with Tone
mapping collapsed, and move a few percent with where you cut the windows out.
The recipes for the measurements, and the numbers they gave, are in
`REFERENCE.md`'s row for this chapter.

- [ ] **The script** (optional). `python make_island.py` (the Appendix) prints
      the land's shares within a point or two of the Appendix's: four-fifths
      grass. Another Python or C library makes another set of the three files
      (Chapter 36 section 7), so check the shares and **Show materials** against
      section 2's picture, not hashes. `--quick` leaves `IslandQuick.png` as it
      was.
- [ ] **Loaded.** The log has the map's line, six tint lines, each tinted mean
      within 1/255 of its material's colour, six height lines, and the
      textures' line; **Ground** reads **Map 1024 x 1024, 6 weights** and
      **Ground textures 6 x 1024 x 1024**.
- [ ] **Show materials.** Probes with **Show materials** ticked: at **Shore**,
      (800, 600) reads (243, 218, 124), the sand's false colour exactly; at
      **Cliff**, (640, 300) reads (188, 188, 188), rock's; at **Snow**,
      (640, 600) reads (252, 251, 252), the readout's Snow 99 %; at **Stream**,
      (400, 294), on the soil to the left, reads (157, 116, 65), soil with a
      little grass.
- [ ] **The CPU agrees with the GPU.** **Stream**, then hold the right mouse
      button on the scene and drag down until the camera looks straight down
      (section 7 gives the rate and the stop), and tick **Show materials**.
      The ground under the camera is flat there, and the readout says Grass
      62 % and Soil 38 %: 0.62 x (0.1, 0.6, 0.1) + 0.38 x (0.35, 0.15, 0.05),
      encoded, is (122, 175, 80), and the pixel at (640, 360) reads (122, 175,
      80).
- [ ] **Chapter 37, untouched.** Untick **Ground materials**: the frame is
      Chapter 37's. At the viewpoint and in **Wood**, with the clouds off (the
      **Sky** header's **Clouds** box) so that the sky holds still, every pixel
      outside the panels is the same as a build of Chapter 37's code, byte for
      byte.
- [ ] **Nothing changes far away.** At the viewpoint, **Detail up close** on and
      off give the same picture, byte for byte. Control: set `DETAIL_FAR` to
      2,000 and build, and tens of thousands of pixels differ, by up to 9
      levels of 255, because ground far below the camera reads the
      photographs. Put it back.
- [ ] **Detail is there.** **Meadow**: the grass in the bottom rows has a grain,
      and without **Detail up close** it is smooth. Measured as the standard
      deviation of each pixel's luminance less the mean of the 5 x 5 pixels
      around it, over the bottom 200 rows right of the panel, there is eleven
      times as much with the photographs as without.
- [ ] **No seam at the fade.** **Meadow**, **Detail up close** on and off, with
      the clouds off: the ground 100 to 300 m away keeps its colour within
      1.2 % (section 10), and no line runs across it.
- [ ] **Normal check.** Make section 7's temporary edit, build, press
      **Meadow** and look straight down at the grass, as section 7 says: a
      field of grey domes, every one lit on the side toward the sun. Negate `B`
      in `bumped` (`B = -cross(N, T)`, as a DirectX normal map would) and the
      domes lit from below along one axis become dents. At **Cliff** the domes
      stand on the face as well, upright in the rock's side projections, each
      lit like its neighbours. Put `B` back, and take the edit out.
- [ ] **Show reads.** At the viewpoint, every pixel is green. At **Cliff**,
      none is: the face is yellow where rock is read from two sides, and orange
      where it is read from three, or meets the scree. Counted on the
      reference run, with the bands' flat colours in place of the half-and-half
      mix (the view's line made `color = readsColor(groundReads);`) so that
      each pixel's band reads back exactly, **Cliff** is 42 % yellow and 58 %
      orange, a point either way with how you cut the windows out. Put the line
      back.
- [ ] **Shore.** At **Shore**, the sand runs on under the water on the right,
      with no seam where the water begins; with **Show materials** the beach is
      yellow and the water is not. Only the ripples stop at the edge, where the
      floor is lit flat.
- [ ] **Snow.** At **Snow**, the ridge under the camera is white in **Show
      materials**, and with it off a white with the photograph's grain, blue
      where the sky lights it; the faces of the peak beyond, too steep to hold
      snow, read (188, 188, 188), rock, with snow only on its gentler
      shoulders.
- [ ] **Clumped borders.** At **Meadow**, the rock meets the grass in clumps.
      Comment out the `heightBlend(color, b);` line in `groundDetail`, build,
      and look again: section 6's cross-fade, a pale band of rock printed over
      the grass. Put it back.
- [ ] **Cliffs without streaks.** At **Cliff**, no streaks. Make
      `triplanarWeights` return `vec3(0.0, 1.0, 0.0)`, rock from above only,
      and build: the face's grain is drawn out down the slope into streaks. Put
      it back.
- [ ] **No grid.** At **Meadow**, from 30 m to 150 m away, no grid of repeating
      tiles.
- [ ] **The variation.** Set `VARIATION` to 0, build, and compare the viewpoint
      and **Meadow** with the finished demo's: only the lighter and darker
      patches of section 3 go. At the viewpoint they change a pixel's
      brightness by −10.8 % to +9.6 % (5th to 95th percentile), over the ground
      below the horizon outside the panels, and the mean colour of all that
      ground by less than a fifth of a level, because the patches average out.
      Put it back.
- [ ] **Missing files.** Rename `IslandMaterials1.png` beside the executable
      and run: one warning beginning "No material map", **Map none**, and
      Chapter 37's frame. Name it back, rename
      `Assets/Terrain/Ground/Snow/Height.png`, and run: one warning, "No ground
      textures:" and the file, **Ground textures none: flat colours**, and
      section 4's picture. The demo runs on in both. Name it back.
- [ ] **Hygiene**, as the index's
      [Conventions](../VulkanTutorial.md#conventions-every-chapter-uses) list it
      (4x MSAA, a resize, validation silent), with synchronization validation on.
- [ ] **The layers' positive control.** In `uploadLayers`, give barrier (2) a
      layer count of 1 (the `layers` after `level - 1, 1,`), build, and run:
      validation reports `VUID-vkCmdBlitImage-srcImageLayout-00221` at the
      first blit, "Cannot use VkImage ... (layer 1, mip 0) with specific layout
      VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL that doesn't match the previous
      known layout VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL": layer 1 never left
      the copy's layout. Beside it come `SYNC-HAZARD-READ-AFTER-WRITE` at the
      same blits, which read layer 1 with no barrier after the write, and
      `VUID-VkImageMemoryBarrier2-oldLayout-01197` at the next barrier, which
      moves layer 1 out of a layout it is not in. Put it back.
- [ ] **The stages' positive control.** In `CreateIslandSet`, after the loop,
      set
      `bindings[1].stageFlags = VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_COMPUTE_BIT;`,
      build, and run: validation reports
      `VUID-VkGraphicsPipelineCreateInfo-layout-07988` at
      `vkCreateGraphicsPipelines`: the fragment shader "uses descriptor [Set 1,
      Binding 1, variable "groundMap"]
      (VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER) but the
      VkDescriptorSetLayoutBinding::stageFlags was
      VK_SHADER_STAGE_VERTEX_BIT|VK_SHADER_STAGE_COMPUTE_BIT". A driver may
      still make the pipeline; the layer is what says it is wrong. Put it back.

---

## Where to go from here

Section 11's table says what the chapters to come read from this one.

What this chapter did not build, and when it becomes worth building:

- **Stochastic or hex tiling**, when a big uniform meadow still shows its
  repeat: each pixel blends a few randomly offset copies of the tile, chosen
  on a grid of triangles (Heitz and Neyret, 2018), or on hexagons whose copies
  are turned too (Mikkelsen, 2022), so no copy lines up with the next. Three
  reads where there was one.
- **Two scales per layer**: the same photograph read again four or five times
  larger, multiplied in, to break the repeat with its own detail. It would
  also let a photographed grass replace the generated one: Poly Haven's
  *Grass Ground* repeats every 2.5 m in rows that a second scale hides in part.
- **Parallax or displacement** from the heights already in the colour's alpha:
  parallax occlusion mapping marches the view ray through them per pixel, and
  tessellation could move the near vertices by them. Neither adds a texture.
- **Wet sand and a wet sheen** where the waves reach, when the coast's waves
  arrive: a band along the shore, darker and glossier, moving with the
  run-up.
- **Overlays at run time**, a season's snow line, leaf litter under the trees,
  paths between the villages, painted into a small map of their own and
  blended over these weights.
- **More materials**, in a third layer of the map: three more weights, no new
  image, one more read.
- **Compressed textures**, BC7 for colour and BC5 for normals, through KTX2:
  a quarter of the memory and of the bandwidth, for a feature check and a
  loader.
- **Virtual texturing**, when the ground needs a unique texture everywhere
  rather than tiles: a project of its own.
- **Decals** for one-off marks, a burnt patch, a cart track.
- **A normal per pixel from the heightmap at distance**, so the far hills show
  their ridges in the light where the vertex normals are a ring cell apart.

Next: [39 — Plants](39-Plants.md)

---

## Sources

- Hans Theobald Beyer, *Implementation of a method for hydraulic erosion*, 2015
  (Chapter 36's source): the droplets whose footprints section 1 records.
- ambientCG, CC0: *Ground 055 L*,
  <https://ambientcg.com/view?id=Ground055L>; *Grass 004*, made procedurally,
  <https://ambientcg.com/view?id=Grass004>; *Ground 048*,
  <https://ambientcg.com/view?id=Ground048>; *Rock 045*,
  <https://ambientcg.com/view?id=Rock045>; *Snow 006*,
  <https://ambientcg.com/view?id=Snow006>. Downloaded 2026-10-11.
- Dimitrios Savva, *Gray Rocks*, Poly Haven, CC0,
  <https://polyhaven.com/a/gray_rocks>. Downloaded 2026-10-11.
- Charlotte Baglioni, *Grass Ground*, Poly Haven, CC0,
  <https://polyhaven.com/a/grass_ground>, 2.51 m: the photographed grass
  section 5 passed over for its rows. Looked at, not used.
- The Khronos Group, *Vulkan Specification*, "Image Copies with Scaling"
  (`vkCmdBlitImage`: an sRGB source is converted to linear before filtering),
  and *The OpenGL Shading Language*, "Derivative Functions" (derivatives are
  undefined in non-uniform control flow).
- Ubisoft, *Terrain Rendering in Far Cry 5*, GDC 2018: the same terrain data
  feeds the trees, grass and rocks.
- Guerrilla Games, *GPU-Based Run-Time Procedural Placement in Horizon: Zero
  Dawn*,
  https://www.guerrilla-games.com/read/gpu-based-procedural-placement-in-horizon-zero-dawn:
  placement by rules over world maps such as humidity and distance to a river.
- Eric Heitz and Fabrice Neyret, *High-Performance By-Example Noise using a
  Histogram-Preserving Blending Operator*, Proceedings of the ACM on Computer
  Graphics and Interactive Techniques 1(2), 2018 (HPG 2018): tiles blended
  from randomly offset copies on a triangle grid, with no visible repeat.
- Morten S. Mikkelsen, *Practical Real-Time Hex-Tiling*, Journal of Computer
  Graphics Techniques 11, 2022, <https://jcgt.org/published/0011/03/05/>: the
  same on hexagons, with turned copies, and cheap enough for real time.

---

## Appendix — the material map in `make_island.py`

Reference for section 1: the script that writes the map. It is on the `start`
branch at `Assets/Terrain/make_island.py` (489 lines, plain Python 3 with the
standard library only), the file Chapter 36's appendix describes: that is the
finished script, with everything this chapter adds, and it still makes the same
`Island.png`, byte for byte. Both maps are on `start` beside the heightmap, so
you need to run it only to make your own, from your own island or with other
streams or another snow line. From `Assets/Terrain/`, `python make_island.py`
takes two to three minutes and up to 2.7 GiB of memory, prints its steps, with
step 2b's line new, and, before each file's SHA-256 at the end, what the land
is made of:

```text
land: sand 6.89 %, grass 80.77 %, soil 2.05 %, scree 4.44 %, rock 5.80 %, snow 0.04 %
snow 0.148 km2
```

A run writes `Island/Island.png`, `Island/IslandMaterials0.png` and
`Island/IslandMaterials1.png` as one set. On another Python or C library it
makes a different island (Chapter 36 section 7), and a map that fits that
island: never mix them, and check a run by the shares above, within a point or
two, and by **Show materials** against section 2's picture. Lower `SOIL_FROM`
and `SOIL_TO` for more streams of soil, and wider ones: 90 and 260 paint 7 % of
the land brown, where 150 and 420 paint 2 %. Raise `SNOW_LOW` and `SNOW_HIGH`
for less snow, lower them for a winter island; Chapter 36's own snow line,
820-900 m, would leave 0.017 km², a few ledges. `--quick` still writes
`IslandQuick.png`, unchanged, and now two 256 x 256 maps beside it,
`IslandMaterials0Quick.png` and `IslandMaterials1Quick.png`, which nothing
loads. The two maps are in the same Git LFS folder as the heightmap,
`Assets/Terrain/Island/`, so they need no new line in `.gitattributes`.

What this chapter adds to Chapter 36's script, in the order of the file:

| Where | What it adds |
| --- | --- |
| the imports | `hashlib` and `itertools` |
| `footprints`, above `erode` | a dictionary for the two counts below, which every call of `erode` refills; after step 2 it holds the finest pass's, on the 32 m grid the map is made on |
| `erode` | two zeroed arrays, `visits` and `settled`, and three lines that record each step in the cell the drop is nearest to |
| step 2b: constants | `SOIL_FROM`, `SOIL_TO` (which streams are soil), `SNOW_LOW`, `SNOW_HIGH`, `SNOW_STEEP_FROM`, `SNOW_STEEP_TO` (where snow lies), and `MATERIALS`, the order of the six weights |
| step 2b: `box_blur`, `slope_grid` | the mean of the cells around each cell, by running sums, so that its cost does not grow with the radius; the slope from the cells either side, as section 1 says |
| step 2b: `make_materials` | the six weights of every cell, from the four signals of section 1, painted in order |
| step 2b: `write_png_rgb`, `sha256` | an 8-bit RGB PNG with text notes that name the channels, the seed and the cell size (Chapter 36's `write_png` with colour type 2); a file's fingerprint |
| `main` | step 2b between the `PEAK` scale and step 3, writing both files; at the end, the shares, the snow's area and the three files' hashes |

### The island must not move

`Island.png` is committed, and Chapters 36 and 37 measured everything on it, so
the map has to come from the same run without changing one byte of it. One more
draw from `rng` anywhere would move every draw after it, and the island with
them; and floats round at every step, so a sum worked out in another order,
even a faster one that is equal on paper, gives other heights. The four rules
that follow are written at the top of step 2b, for whoever edits the script
next:

```python
# Rules that keep Island.png byte for byte the same while the map is made beside it:
#   1. recording the footprints (erode) draws nothing from rng;
#   2. erode's four `h[...] += amount * ...` lines are never rewritten (precomputing their weights would
#      change the order of the rounding, and the heights);
#   3. the map is made after the PEAK scale and before step 3, from heights step 3 does not change;
#   4. any noise a map ever needs comes from its own random.Random(SEED + 38), never from rng.
```

### The footprints, in `erode`

The two counts are kept in a dictionary at the top of step 2, which every call of
`erode` refills. The passes run from coarse to fine, so after step 2 it holds the
finest pass's:

```python
# Chapter 38: erosion's footprints, for the material map (step 2b). Each call of erode below replaces them, so
# after step 2 they are the last pass's, on the finest grid: how many droplet steps began nearest each cell,
# and how much soil they dropped there (in cells of height, as erode's heights are).
footprints = {}
```

`erode` makes the two arrays, zeroed, with its other locals:

```python
    visits = footprints["visits"] = array.array("d", bytes(8 * w * w))      # Chapter 38
    settled = footprints["settled"] = array.array("d", bytes(8 * w * w))    # Chapter 38
```

and records each step, after `amount` is decided and before it changes the
heights. `fx` and `fy` say where in its cell the drop stands, so the nearest of
the four cells around it is one further along x if `fx` is half or more, and a
row further if `fy` is:

```python
            # Chapter 38: the footprint, in the cell the drop was nearest to. It draws nothing from rng and
            # leaves the four lines below as they are, so the heights come out exactly the same.
            near = i + (fx >= 0.5) + (fy >= 0.5) * w
            visits[near] += 1.0
            if amount > 0.0:
                settled[near] += amount
```

### The rules, in `make_materials`

`make_materials` is section 1's rules, line for line. For every cell, `h` is
its height, `s` its slope, `v` the drop steps through it and `d` the soil
dropped there (both averaged over the cells around it), and `n` how much of the
cells around is cliff; `smoothstep` is the script's. Every sea cell is sand,
the sea floor at the waterline; on land the six are painted in order, each mask
laid over what is there:

```python
            if h <= 0.0:
                weights = (1.0, 0.0, 0.0, 0.0, 0.0, 0.0)
            else:
                soil = smoothstep(SOIL_FROM, SOIL_TO, v)
                scree = smoothstep(0.04, 0.30, n) * (0.25 + 0.75 * smoothstep(10.0, 70.0, d))
                rock = smoothstep(0.65, 1.05, s)
                rock += (1.0 - rock) * 0.5 * smoothstep(640.0, 800.0, h)
                snow = smoothstep(SNOW_LOW, SNOW_HIGH, h) * (1.0 - smoothstep(SNOW_STEEP_FROM, SNOW_STEEP_TO, s))
                sand = (1.0 - smoothstep(2.5, 9.0, h)) * (1.0 - smoothstep(0.12, 0.30, s))
                # Grass first, then each layer over what is there: what it covers keeps (1 - its mask).
                weights = [0.0, 1.0, 0.0, 0.0, 0.0, 0.0]
                for index, mask in ((2, soil), (3, scree), (4, rock), (5, snow), (0, sand)):
                    weights = [weight * (1.0 - mask) for weight in weights]
                    weights[index] = mask
```
