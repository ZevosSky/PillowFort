# 58 — Grass to the Horizon, page 2: what the capture knows

> **Reference support:** named prepared-exercise and native-regression commands
> in this lesson run from the [reference checkout](../BranchWorkflow.md#prepared-reference-exercises).
> The growing chapter implementation remains in your learning checkout.

**Chapter 58's pages:** [1. Sections 1 to 3 — How much ground a field hides](58-Grass-To-The-Horizon.md) · **2. Sections 4 and 5 — What the capture knows** · [3. Sections 6 and 7 — The canopy](GrassToTheHorizonCanopy.md) · [4. Sections 8 to 10 — How far the cards go](GrassToTheHorizonReach.md).

Page 1 worked out how much ground a random field of clumps hides
([section 2](58-Grass-To-The-Horizon.md#2-how-much-ground-a-field-hides)) and which share of the population the cards
leave for the canopy ([section 3](58-Grass-To-The-Horizon.md#3-two-forms-of-one-field)). Both are arithmetic in
`GrassCanopy.h`, checked by the supplied test, now at stage 2. Nothing on screen has changed. Keep
`..\SandboxGame-before-58`, the build you copied in section 1: both checkpoints on this page compare frames with it.
The prerequisites are the chapter's, listed in its [header](58-Grass-To-The-Horizon.md).

## 4. Reading the capture back

The law needs A(e), the area one clump blocks when seen from elevation e, and two things more that section 7 will
want: how high the clump's cover reaches, and what a ray sees of it from the tips down. All of it is in the clump
capture of [Chapter 46](46-Capturing-Grass-Clumps.md#2-put-views-where-the-eye-goes). `GrassClumpAtlas` bakes 4
variants of a clump from 8 azimuths and 7 elevations, 224 layers of three 128-pixel images (the material, with the
blade's height in red and coverage in alpha; the normal, with depth in alpha; and the blade's face normal), and blits
each down a chain of 8 mips. The mips are premultiplied
([section 3 there](46-Capturing-Grass-Clumps.md#3-a-mip-is-not-a-new-material)): the bake clears to 0 and writes alpha
1 where a blade covers, so after averaging, a texel's alpha is the share of it a blade covers and its other channels
are their values times that share.

So mip 3 holds the answers already averaged. Each of its layers is 16 by 16 texels, small enough to read back whole:
3 images × 224 layers × 256 texels × 4 halves × 2 bytes is 1,376,256 bytes, 1.3 MB, once. And 16 rows are still fine
enough to tell a clump's tips from its roots, which a coarser mip would blur together. Mip 3's coverage, summed over a
layer, is the share of the card's square a clump covers from that view; times the card's area it is A(e).

**Only Horizon asks.** The Grass demo rebakes its capture whenever its clump settings change, and both of its frames in
flight could bake: a single host buffer would then be written by two frames whose fences are waited at different
times. Horizon bakes once, at its first frame, so it alone asks for the copy. The Grass demo records no copy and no host
barrier; only its last barrier's source gains `COPY`, which waits for nothing.

**Where the copy sits.** `GrassClumpAtlas::Record` writes mip 0 of every layer by drawing, then for each image blits
mip 1 from mip 0, mip 2 from mip 1, and so on down to mip 7. After each blit, one barrier moves the mip it wrote from
`TRANSFER_DST_OPTIMAL` to `TRANSFER_SRC_OPTIMAL`, with the blit stage as both its source and its destination: it
names the next blit, the only reader that chain knows. After the chain, one last barrier moves all 8 mips to
`SHADER_READ_ONLY_OPTIMAL` for the fragment shaders that sample them. The copy of mip 3 goes between the chain and that
last barrier, and it needs three dependencies.

1. **Mip 3's blit, then the copy.** The barrier after mip 3's blit made its writes visible to the blit stage only, and
   a copy runs in the copy stage. So before the copy: a memory barrier from `BLIT` / `TRANSFER_WRITE` to `COPY` /
   `TRANSFER_READ`. Mip 3 is already in `TRANSFER_SRC_OPTIMAL`, the layout the copy reads it in.
2. **The copy, then the layout change.** A layout change writes the image, and the last barrier was written when
   the blits were all it had to wait for. What it must name now is the attempt below.
3. **The copy, then the host.** The copy wrote the buffer, and the CPU reads it after the frame's fence: Chapter 20,
   section 9's barrier, `COPY` / `TRANSFER_WRITE` to `HOST` / `HOST_READ`, once after all three images' copies.

The buffer's layout follows from one `VkBufferImageCopy` per image: all 224 layers of mip 3 in one region, written
tightly packed, layer after layer, each layer 16 rows of 16 texels, row 0 the top of the image. Each image starts at
its index times one image's bytes. The bake flips y, so row 0 holds the blade tips.

The CPU takes the copy after the fence of the slot that recorded it. Horizon has two frames in flight: the bake is
recorded in frame 1, slot 0, whose fence is next waited at frame 3, so the table arrives on frame 3, and the canopy
draws from then on. No checkpoint in this chapter reads frame 1 or 2.

<a id="ch58-read-back"></a>

### Attempt CH58-read-back: three barriers around one copy

Predict first. The last barrier of each image's chain moves the whole mip chain to `SHADER_READ_ONLY_OPTIMAL` with
source `BLIT` and accesses `TRANSFER_READ | TRANSFER_WRITE`. With the copy of mip 3 placed just before it, which
source stage must it name now, and does its source access change? And why is the barrier from the copy to the host,
which the CPU's read needs anyway, not enough to protect the copy from the layout change?

**Acceptance:** the copy is recorded only when the atlas was asked for it; the last barrier's source is
`BLIT | COPY`; and two controls fire in a Debug run: with the barrier before the copy naming the blit stage, not the copy's, sync
validation
reports the copy reading what the blit's chain wrote; with `COPY` taken out of the last barrier's source, it reports the
layout change writing what the copy reads. Stage 3 of the supplied test folds a capture built by hand in the copy's
layout and passes.

**Transfer:** the Grass demo could capture too, with one host buffer per frame in flight. What would it need, beyond
the buffers, to fold the right copy after a rebake?

<details>
<summary>Hint 1: what a layout change is</summary>

Chapter 4's third question, what must be visible, has an answer for a layout change: nothing is read, but the image's
memory is rewritten. Who reads mip 3 last before it?

</details>

<details>
<summary>Hint 2: what a barrier orders</summary>

A barrier orders what came before it in its first scope with what comes after it in its second. The host barrier's
second scope is the host. Does the layout change belong to it?

</details>

<details>
<summary>Hint 3: where the reads are</summary>

The final barrier's source access is already `TRANSFER_READ | TRANSFER_WRITE`. What is missing is the stage that did
the read.

</details>

<details>
<summary>Worked solution: `BLIT | COPY`, the same accesses, and a barrier for each side of the copy</summary>

The last barrier names `BLIT | COPY` as its source stages: the layout change must wait for the copy's read, a write
after a read, which needs an execution dependency and no more, so `TRANSFER_READ | TRANSFER_WRITE` stay as they are.
The host barrier orders the copy's write before the host's read; the layout change is a device operation that the
host barrier's second scope does not contain, so it does nothing for it.

Without a copy, the Grass demo's case, `COPY` in the source stages waits for nothing, and naming it there costs nothing,
so the barrier is written once, with `COPY` always.

The two controls, both inside one submission, where sync validation can see them:

- **A:** in the `memoryBarrier` before `vkCmdCopyImageToBuffer` (the one whose comment says "which is a COPY-stage"),
  change the destination stage `VK_PIPELINE_STAGE_2_COPY_BIT` to `VK_PIPELINE_STAGE_2_BLIT_BIT`, so it orders the
  blits with more blits and the copy with nothing. A Debug run at Wind edge prints three
  `SYNC-HAZARD-READ-AFTER-WRITE` at `vkCmdCopyImageToBuffer`, one for each image: the copy reads mip 3, which the
  layout change after its blit last wrote.
- **B:** in the last barrier, change `VK_PIPELINE_STAGE_2_BLIT_BIT | VK_PIPELINE_STAGE_2_COPY_BIT` to
  `VK_PIPELINE_STAGE_2_BLIT_BIT`. The Debug run prints three `SYNC-HAZARD-WRITE-AFTER-READ` at
  `vkCmdPipelineBarrier2`, one for each image: the layout change writes what `vkCmdCopyImageToBuffer` read.

Put both back. The host barrier has no control: sync validation does not look across a host fence wait
([Chapter 36, section 8](36-Terrain-To-The-Horizon.md#8-the-heightmap-on-the-gpu)), so it is argued by
[Chapter 4's three questions](04-Commands-And-Synchronization.md#5-barriers-and-the-three-questions-they-answer): the
copy wrote the buffer; the host reads it; the copy's writes must be available to the host. It is the appendix's row
"Readback copy visible to the CPU".

**Answer to the transfer.** It must know which bake each copy holds. A rebake while a copy is still in flight records
a second copy into the other slot's buffer, and the first fence to arrive would hand over the older one. The source
key the atlas already keeps would have to travel with each copy, and the fold would take only a copy whose key is the
current one, with the clump size and density it was baked with: the table keeps the bake's values, and Horizon has no
control of either at run time.

</details>

**`GrassCanopyTable.h`.** The fold is CPU code, so the supplied test can call it, and it goes in a file of its own
rather than inside `GrassField`. Its header states the buffer's layout once, so the fold and the test agree on it. The
table holds per elevation row the coverage (weighted so that, times the card area, it is the mean area a clump
projects), and per image row of the 0-degree view, the row's mean alpha `c`, where up the blade it sits `t`, its mean
normal and its mean face normal, in the view's own basis. In `Source/PillowFort/Demos/Grass/`, create
`GrassCanopyTable.h`:

```cpp
///========================================================
/// @author Gary Yang
/// @brief The clump capture read back and folded on the CPU into what a canopy needs: coverage, height and facing
/// @copyright (C) Gary 2026
///========================================================
#pragma once
#include "Grass/GrassClumpSource.h"
#include <glm/glm.hpp>
#include <array>
#include <cstdint>
#include <vector>

namespace pf::demos::grass
{

// The capture is mip 3 of the three clump images: 16 x 16 texels a layer, small enough to read back and still fine
// enough to tell the clump's height rows apart.
inline constexpr uint32_t GRASS_CAPTURE_MIP = 3;
inline constexpr uint32_t GRASS_CAPTURE_SIDE = GRASS_CLUMP_TILE >> GRASS_CAPTURE_MIP;   // 16 rows of 16 texels
inline constexpr uint32_t GRASS_CAPTURE_HALVES =
    GRASS_CLUMP_ATTACHMENTS * GRASS_CLUMP_LAYERS * GRASS_CAPTURE_SIDE * GRASS_CAPTURE_SIDE * 4;

// Folded once, on the CPU. "Row" in `c`, `t`, `normal` and `face` is an image row of mip 3 at elevation row 1 (0 degrees):
// row 0 is the top of the image, which holds the blade tips.
struct GrassCanopyTable
{
    bool  valid = false;
    // Per elevation row: mean_v(coverage_v x side_v^2) / mean_v(side_v^2), so coverage x cardArea is exactly the mean over
    // the variants of (coverage_v x side_v^2) x E[scale^2], the area a clump projects. Not a product of two means.
    std::array<float, 7>      coverage{};
    std::array<float, 16>     c{};             // mean alpha of the image row, over the 32 layers of elevation row 1
    std::array<float, 16>     t{};             // sum of material.x / sum of alpha: where up the blade the row sits
    std::array<glm::vec3, 16> normal{};        // mean normal of the covered texels, in the view basis (right, up, toward the eye)
    std::array<glm::vec3, 16> face{};          // mean face normal, flipped toward the eye, same basis
    float     wholeT = 0.0f;                   // the same three means over all 16 rows
    glm::vec3 wholeNormal{ 0.0f };
    glm::vec3 wholeFace{ 0.0f };
    float     cardArea = 0.0f;                 // metres squared: mean bounds.w^2 times E[scale^2]
    float     layerHeight = 0.0f;              // metres: mean_v(side_v x covered image rows / 16) x E[scale], E[scale] = 1
    float     clumpsPerSquareMetre = 0.0f;
};

// The buffer GrassClumpAtlas::TakeCapture returns holds three images back to back (material, normal and depth, face
// normal), each of them layer after layer, each layer 16 rows of 16 texels, 4 halves a texel (red, green, blue, alpha), row
// 0 the top of the image: the bake flips y, so row 0 holds the blade tips. A layer is (variant * 7 + elevation row) * 8 +
// azimuth, as GrassClumpBake.vert.glsl decodes it. The images are premultiplied by coverage: the bake clears to 0 and writes
// alpha 1 where a blade covers, and the mips average, so alpha is the covered share of a texel and the other channels are
// their values times it. Only the material image's alpha is coverage; the normal image keeps depth in its alpha.
GrassCanopyTable foldCanopyTable(const std::vector<uint16_t>& halves, const GrassParameters& parameters);

} // namespace pf::demos::grass
```

**`GrassCanopyTable.cpp`.** Four things are folded. The coverage per elevation: each variant's card is a square of its
own side, so the area a clump projects is the mean over the variants of coverage times side², not the product of two
means. The rows of the 0-degree view (elevation row 1): because the texels are premultiplied, a row's mean is a sum
divided by the sum of alpha, which weighs a sliver of a covered texel as a sliver; dividing each texel by its own alpha
first would weigh it like a whole one. The normals are turned into the view's basis as the fragment kernel orients
them. The layer's height: for each variant, its side times the share of the 16 rows that have any cover, averaged; the
generator's scale is uniform about 1, so its mean is 1, and its mean square, 1 + clumpHeight² / 3, scales the card's
area. In the same folder, create `GrassCanopyTable.cpp`:

```cpp
///========================================================
/// @author Gary Yang
/// @brief The clump capture read back and folded on the CPU into what a canopy needs: coverage, height and facing
/// @copyright (C) Gary 2026
///========================================================
#include "PillowFort/Demos/Grass/GrassCanopyTable.h"
#include <glm/gtc/packing.hpp>
#include <algorithm>

namespace pf::demos::grass
{

GrassCanopyTable foldCanopyTable(const std::vector<uint16_t>& halves, const GrassParameters& parameters)
{
    constexpr uint32_t SIDE = GRASS_CAPTURE_SIDE;
    GrassCanopyTable table;
    if (halves.size() != GRASS_CAPTURE_HALVES) { return table; }
    auto texel = [&](uint32_t image, uint32_t layer, uint32_t y, uint32_t x)
    {
        const size_t base = ((size_t(image) * GRASS_CLUMP_LAYERS + layer) * SIDE * SIDE + size_t(y) * SIDE + x) * 4;
        return glm::vec4(glm::unpackHalf1x16(halves[base]), glm::unpackHalf1x16(halves[base + 1]),
                         glm::unpackHalf1x16(halves[base + 2]), glm::unpackHalf1x16(halves[base + 3]));
    };
    auto layerOf = [](uint32_t variant, uint32_t row, uint32_t azimuth)
    {
        return (variant * GRASS_CLUMP_ELEVATIONS + row) * GRASS_CLUMP_AZIMUTHS + azimuth;
    };

    // Each variant's card is a square of its own side, and its coverage is a share of that square. So the area a clump
    // projects is the mean over the variants of (coverage x side^2), not a product of two means. The table stores
    // coverage[row] = mean_v(coverage_v x side_v^2) / mean_v(side_v^2) and cardArea = mean_v(side_v^2) x E[scale^2], so
    // that coverage[row] x cardArea is exactly that mean area times E[scale^2], and nothing downstream has to know.
    std::array<double, GRASS_CLUMP_VARIANTS> sideOf{};
    double sideSquareSum = 0.0;
    for (uint32_t variant = 0; variant < GRASS_CLUMP_VARIANTS; ++variant)
    {
        sideOf[variant] = double(grassClumpBounds(parameters, variant).w);
        sideSquareSum += sideOf[variant] * sideOf[variant];
    }
    const double divisorSides = std::max(sideSquareSum, 1e-12);

    // The share of the view a clump covers, at each elevation.
    for (uint32_t row = 0; row < GRASS_CLUMP_ELEVATIONS; ++row)
    {
        double weighted = 0.0;
        for (uint32_t variant = 0; variant < GRASS_CLUMP_VARIANTS; ++variant)
        {
            double sum = 0.0;
            for (uint32_t azimuth = 0; azimuth < GRASS_CLUMP_AZIMUTHS; ++azimuth)
            {
                const uint32_t layer = layerOf(variant, row, azimuth);
                for (uint32_t y = 0; y < SIDE; ++y)
                {
                    for (uint32_t x = 0; x < SIDE; ++x) { sum += texel(0, layer, y, x).a; }
                }
            }
            const double coverage = sum / double(GRASS_CLUMP_AZIMUTHS * SIDE * SIDE);   // this variant's share of its own square
            weighted += coverage * sideOf[variant] * sideOf[variant];
        }
        table.coverage[row] = float(weighted / divisorSides);
    }

    // Elevation row 1 is 0 degrees, the view along the ground. The texels are premultiplied, so a mean over the covered
    // texels is a sum divided by the sum of alpha; dividing each texel by its own alpha first would weigh a sliver of a
    // texel like a full one.
    std::array<double, SIDE> alpha{}, tSum{};
    std::array<glm::dvec3, SIDE> normalSum{}, faceSum{};
    std::array<std::array<double, SIDE>, GRASS_CLUMP_VARIANTS> variantAlpha{};   // alpha summed over azimuths and texels
    for (uint32_t variant = 0; variant < GRASS_CLUMP_VARIANTS; ++variant)
    {
        for (uint32_t azimuth = 0; azimuth < GRASS_CLUMP_AZIMUTHS; ++azimuth)
        {
            const uint32_t layer = layerOf(variant, 1, azimuth);
            // The basis of this layer's view: its right, its up, and the direction toward the eye.
            const glm::vec3 direction = grassClumpDirection(azimuth, 1), right = grassClumpRight(azimuth);
            const glm::vec3 up = glm::cross(direction, right);
            for (uint32_t y = 0; y < SIDE; ++y)
            {
                for (uint32_t x = 0; x < SIDE; ++x)
                {
                    const glm::vec4 material = texel(0, layer, y, x);
                    if (material.a <= 0.0f) { continue; }
                    const glm::vec3 n = glm::vec3(texel(1, layer, y, x)), f = glm::vec3(texel(2, layer, y, x));
                    const glm::vec3 oriented = grassClumpOrientNormal(n, f, direction);   // as the fragment kernel orients it
                    const glm::vec3 flipped = glm::dot(f, direction) < 0.0f ? -f : f;     // and flips the face
                    alpha[y] += material.a;
                    variantAlpha[variant][y] += material.a;
                    tSum[y] += material.x;
                    normalSum[y] += glm::dvec3(glm::dot(oriented, right), glm::dot(oriented, up), glm::dot(oriented, direction));
                    faceSum[y] += glm::dvec3(glm::dot(flipped, right), glm::dot(flipped, up), glm::dot(flipped, direction));
                }
            }
        }
    }
    double totalAlpha = 0.0, totalT = 0.0;
    glm::dvec3 totalNormal(0.0), totalFace(0.0);
    for (uint32_t y = 0; y < SIDE; ++y)
    {
        table.c[y] = float(alpha[y] / double(GRASS_CLUMP_VARIANTS * GRASS_CLUMP_AZIMUTHS * SIDE));
        // A row nothing covers has no mean: its sums are 0, so the divisor only has to keep the division finite.
        const double divisor = std::max(alpha[y], 1e-12);
        table.t[y] = float(tSum[y] / divisor);
        table.normal[y] = glm::vec3(normalSum[y] / divisor);
        table.face[y] = glm::vec3(faceSum[y] / divisor);
        totalAlpha += alpha[y];
        totalT += tSum[y];
        totalNormal += normalSum[y];
        totalFace += faceSum[y];
    }
    const double total = std::max(totalAlpha, 1e-12);
    table.wholeT = float(totalT / total);
    table.wholeNormal = glm::vec3(totalNormal / total);
    table.wholeFace = glm::vec3(totalFace / total);

    // The covered height of a clump: for each variant, its side times the image rows from the first to the last whose mean
    // alpha (over the 8 azimuths and the 16 texels) is above 1e-4, as a share of the 16 rows; then the mean over the
    // variants. The generator's scale is 1 + clumpHeight (2u - 1) for u uniform, so E[scale] = 1.
    double height = 0.0;
    for (uint32_t variant = 0; variant < GRASS_CLUMP_VARIANTS; ++variant)
    {
        int first = -1, last = -1;
        for (uint32_t y = 0; y < SIDE; ++y)
        {
            if (variantAlpha[variant][y] / double(GRASS_CLUMP_AZIMUTHS * SIDE) > 1e-4)
            {
                if (first < 0) { first = int(y); }
                last = int(y);
            }
        }
        if (first >= 0) { height += sideOf[variant] * double(last - first + 1) / double(SIDE); }
    }
    table.layerHeight = float(height / double(GRASS_CLUMP_VARIANTS));

    // The card a clump stands for: the mean square of the capture's bounds, times the mean square of the scale the
    // generator draws, so E[scale^2] = 1 + clumpHeight^2 / 3. With coverage above, the product is the mean projected area.
    table.cardArea = float(sideSquareSum / double(GRASS_CLUMP_VARIANTS)) *
                     (1.0f + parameters.clumpHeight * parameters.clumpHeight / 3.0f);
    const float width = grassClumpWidth(parameters);
    table.clumpsPerSquareMetre = 1.0f / (width * width);
    table.valid = true;
    return table;
}

} // namespace pf::demos::grass
```

**`GrassClumpAtlas.h`.** Below `#include <array>`, add:

```cpp
#include <cstdint>
#include <vector>
```

`EnableCapture` asks for the copy, `Record` learns which frame slot it records for, and `TakeCapture` hands the copy
over once that slot's fence has been waited. Replace the two lines of `Record`'s declaration with:

```cpp
    // Chapter 58 section 4: asks for mip 3 of every layer to be copied to a host buffer once per bake. Only Horizon asks:
    // the Grass demo rebakes when its source changes, and a buffer shared by the frames in flight would be written by two.
    InitializationResult EnableCapture();
    // frameIndex is the frame slot the commands are recorded for; TakeCapture reads the copy back for that slot. Only a
    // capturing atlas uses it, so callers that never capture (the Grass demo's tests) leave it at 0.
    void Record(VkCommandBuffer commandBuffer, VkPipelineLayout layout, VkDescriptorSet grassSet,
                VkShaderStageFlags pushStages, uint32_t frameIndex = 0);
    // True once per bake, after the fence of the frame that recorded it; halves are laid out as GrassCanopyTable.h says.
    bool TakeCapture(uint32_t frameIndex, std::vector<uint16_t>& halves);
```

`frameIndex` defaults to 0, so the Grass demo's tests, which call `Record` and never capture, compile unchanged. Below
`bool m_dirty = true;`, add, with no blank line between:

```cpp
    vulkan_graphics::AllocatedBuffer m_capture{};   // Chapter 58 section 4: the host buffer, empty unless EnableCapture ran
    uint32_t m_captureFrame = 0;                    // the frame slot that recorded the copy
    bool m_capturePending = false;                  // recorded, not yet taken
```

**`GrassClumpAtlas.cpp`.** Below `#include "PillowFort/Demos/Grass/GrassClumpAtlas.h"`, add:

```cpp
#include "PillowFort/Demos/Grass/GrassCanopyTable.h"
#include "PillowFort/ErrorReporting/Log.h"
```

Below `PrepareSource` and its blank line, add `EnableCapture`, with a blank line below it. The buffer is Chapter 20's
readback buffer, host-visible and cached; asking twice keeps the first:

```cpp
InitializationResult GrassClumpAtlas::EnableCapture()
{
    if (!m_context.device) { return InitializationResult::failure("Enabling the grass capture readback needs an initialized atlas."); }
    if (m_capture.buffer) { return InitializationResult::success(); }
    m_capture = createReadbackBuffer(m_context, VkDeviceSize(GRASS_CAPTURE_HALVES) * sizeof(uint16_t));
    if (!m_capture.buffer) { return InitializationResult::failure("Allocating the grass capture readback buffer failed."); }
    return InitializationResult::success();
}
```

Replace `Record`'s first two lines, its signature, with:

```cpp
void GrassClumpAtlas::Record(VkCommandBuffer cb, VkPipelineLayout layout, VkDescriptorSet grassSet,
                             VkShaderStageFlags stages, uint32_t frameIndex)
```

At the end of the loop over the images, after the loop over the mips and its closing brace, the last barrier moves the
chain to `SHADER_READ_ONLY_OPTIMAL`; it is the four lines from
`imageBarrier(cb, image.image, 0, GRASS_CLUMP_MIPS, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,` to
`VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_SHADER_SAMPLED_READ_BIT);`. Replace those four lines with the copy
and the barrier before it, then the last barrier with its new source:

```cpp
        if (m_capture.buffer)
        {
            // Each mip's barrier above names BLIT as the only reader of the mip it wrote, so a copy, which is a COPY-stage
            // read, needs a dependency of its own.
            memoryBarrier(cb, VK_PIPELINE_STAGE_2_BLIT_BIT, VK_ACCESS_2_TRANSFER_WRITE_BIT,
                          VK_PIPELINE_STAGE_2_COPY_BIT, VK_ACCESS_2_TRANSFER_READ_BIT);
            const VkDeviceSize imageBytes = VkDeviceSize(GRASS_CLUMP_LAYERS) * GRASS_CAPTURE_SIDE * GRASS_CAPTURE_SIDE * 8;
            const VkBufferImageCopy copy{
                .bufferOffset = VkDeviceSize(&image - m_images.data()) * imageBytes,
                .imageSubresource = {VK_IMAGE_ASPECT_COLOR_BIT, GRASS_CAPTURE_MIP, 0, GRASS_CLUMP_LAYERS},
                .imageExtent = {GRASS_CAPTURE_SIDE, GRASS_CAPTURE_SIDE, 1}};
            vkCmdCopyImageToBuffer(cb, image.image, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL, m_capture.buffer, 1, &copy);
        }
        // BLIT | COPY: the layout change must wait for the copy's read of the image too. Without a copy (the Grass demo never
        // captures) the COPY stage waits for nothing, and naming it there costs nothing.
        imageBarrier(cb, image.image, 0, GRASS_CLUMP_MIPS, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,
                     VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL, VK_PIPELINE_STAGE_2_BLIT_BIT | VK_PIPELINE_STAGE_2_COPY_BIT,
                     VK_ACCESS_2_TRANSFER_READ_BIT | VK_ACCESS_2_TRANSFER_WRITE_BIT,
                     VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_SHADER_SAMPLED_READ_BIT);
```

`&image - m_images.data()` is the image's index in the array the loop walks, 0, 1 or 2. After the loop over the images
and its closing brace, above `m_dirty = false;`, add the host barrier and the note of which slot recorded the copy:

```cpp
    if (m_capture.buffer)
    {
        // The copies' writes to the buffer, made available to the host, which reads it after this frame's fence: Chapter 20,
        // section 9's barrier. No positive control can show it: sync validation does not look across a host fence wait
        // (Chapter 36 section 8), so it is argued by Chapter 4's three questions (who wrote, who reads, what must be visible).
        memoryBarrier(cb, VK_PIPELINE_STAGE_2_COPY_BIT, VK_ACCESS_2_TRANSFER_WRITE_BIT,
                      VK_PIPELINE_STAGE_2_HOST_BIT, VK_ACCESS_2_HOST_READ_BIT);
        m_captureFrame = frameIndex;
        m_capturePending = true;
    }
```

Below `Record` and its blank line, add `TakeCapture`, with a blank line below it. `readBuffer` is Chapter 20's: it makes
the GPU's writes visible to the CPU's caches and copies out, and it is called only after the slot's fence:

```cpp
bool GrassClumpAtlas::TakeCapture(uint32_t frameIndex, std::vector<uint16_t>& halves)
{
    if (!m_capturePending || m_captureFrame != frameIndex) { return false; }
    halves.resize(GRASS_CAPTURE_HALVES);
    if (auto result = readBuffer(m_context, m_capture, halves.data(), VkDeviceSize(GRASS_CAPTURE_HALVES) * sizeof(uint16_t));
        !result)
    {
        Log::error(result.message());
        return false;
    }
    m_capturePending = false;
    return true;
}
```

In `Shutdown`, below `destroyImage(m_context, m_depth);`, add:

```cpp
    destroyBuffer(m_context, m_capture);
    m_capturePending = false;
```

**`GrassField.h`.** The field owns the atlas, so it passes the request on and keeps the folded table. Below
`#include "PillowFort/Demos/Demo.h"`, add:

```cpp
#include "PillowFort/Demos/Grass/GrassCanopyTable.h"
```

Below the line that declares `Statistics()`, add:

```cpp
    // Chapter 58 section 4: asks the clump bake to be read back and folded into CanopyTable(); only Horizon asks.
    InitializationResult CaptureCanopyStatistics() { return m_atlas.EnableCapture(); }
    const GrassCanopyTable& CanopyTable() const { return m_canopyTable; }
```

Below `GrassStatistics                  m_statistics;`, add, with no blank line between:

```cpp
    GrassCanopyTable                 m_canopyTable;          // Chapter 58 section 4: folded once, after the bake's frame
    GrassParameters                  m_canopyParameters{};   // the parameters the capture was baked from
    std::vector<uint16_t>            m_captureHalves;
```

**`GrassField.cpp`.** The fold needs the parameters the capture was baked from, for the clump's sides and scale. In
`Prepare`, below `m_dispatchClumps[frameIndex] = maximumClumps;`, add:

```cpp
    // Horizon never rebakes, so the latest prepared parameters are the ones the atlas was baked from.
    m_canopyParameters = prepared;
```

`ReadStatistics` already runs once a frame for the slot whose fence was just waited, to read the grass's counters
([Chapter 26, section 8](26-Grass-GPU-Generation.md#8-budgets-you-can-see)), so it is where the copy is taken. At the
top of `ReadStatistics`, above `if (!m_readbackPending[frameIndex]) { return; }`, add:

```cpp
    // The bake's copy arrives once, after the fence of the slot that recorded it.
    if (m_atlas.TakeCapture(frameIndex, m_captureHalves))
    {
        m_canopyTable = foldCanopyTable(m_captureHalves, m_canopyParameters);
        int firstRow = -1, lastRow = -1;
        for (int row = 0; row < int(m_canopyTable.c.size()); ++row)
        {
            if (m_canopyTable.c[row] > 1e-4f)
            {
                if (firstRow < 0) { firstRow = row; }
                lastRow = row;
            }
        }
        Log::info(std::format("Canopy table: coverage at 0 degrees {:.5f}, rows with cover {}..{} (0 = the tips), card area {:.5f} m^2, layer height {:.5f} m, {:.5f} clumps per square metre",
                              m_canopyTable.coverage[1], firstRow, lastRow, m_canopyTable.cardArea,
                              m_canopyTable.layerHeight, m_canopyTable.clumpsPerSquareMetre).c_str());
    }
```

In `Generate`, replace the first line, the call of `m_atlas.Record`, with:

```cpp
    m_atlas.Record(commandBuffer, m_pipelineLayout, m_grassSets[frameIndex], GRASS_STAGES, frameIndex);
```

In `Shutdown`, below `m_islandPush = {};`, add:

```cpp
    m_canopyTable = {};   // Chapter 58 section 4: a detached field has no table
```

**`CoastalArea.cpp`.** Horizon asks. In `Initialize`, below the line that calls `m_grass.Initialize`, add:

```cpp
    if (auto result = m_grass.CaptureCanopyStatistics(); !result) { Shutdown(); return result; }   // Chapter 58 section 4
```

### Checkpoint

Raise the supplied test's stage. In `GrassCanopyTests.cpp`, replace the line that starts `#define PF_TEST_STAGE` with:

```cpp
#define PF_TEST_STAGE 3   // raised in each section of Chapter 58
```

Two files are new, so generate again; build the game in Release and the test in Debug, then run the test:

```powershell
.\GenerateProjects.bat --tutorial-tests
if ($LASTEXITCODE -ne 0) { throw 'Project generation failed.' }
& 'C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe' .\Build\Projects\PillowFort.sln /m /p:Configuration=Release /p:Platform=x64 /t:SandboxGame
if ($LASTEXITCODE -ne 0) { throw 'The game build failed.' }
& 'C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe' .\Build\Projects\PillowFort.sln /m:1 /nr:false /p:CL_MPCount=1 /p:UseMultiToolTask=true /p:MultiProcMaxCount=1 /p:EnforceProcessCountAcrossBuilds=true /p:Configuration=Debug /p:Platform=x64 /t:TutorialGrassCanopyTests
if ($LASTEXITCODE -ne 0) { throw 'The test build failed.' }
& .\Build\Artifacts\Debug\TutorialGrassCanopyTests\TutorialGrassCanopyTests.exe
```

```text
reach 42 m: 360 tiles, 404 examined
reach 120 m: 559 tiles, 624 examined
reach 160 m: 708 tiles, 809 examined
reach 200 m: 896 tiles, 1044 examined
elevation 45 deg, n 12: tau 2.29183, gaps 0.1004 measured, 0.101081 from the law
elevation 25 deg, n 1.5: tau 0.614356, gaps 0.54035 measured, 0.540989 from the law
elevation 8 deg, n 1: tau 1.35894, gaps 0.25803 measured, 0.256934 from the law
elevation 2 deg, n 0.5: tau 2.73456, gaps 0.06594 measured, 0.0649225 from the law
the share and the generator's mean coverage differ by at most 1.0122e-06
at 12 m the cards draw 1 of the clumps
at 20 m the cards draw 0.733333 of the clumps
at 30 m the cards draw 0.45 of the clumps
at 41 m the cards draw 0.00485272 of the clumps
layer height 0.885131 m
card area 1.68387 m^2, 2.25 clumps per square metre
PASS: grass canopy, stage 3 (47 checks)
```

Stage 3 builds a capture by hand in the copy's layout, written from the layout and not from the fold's own indexing:
three images back to back, layer after layer, row 0 the tips, premultiplied as the bake leaves them, with variants that
differ, so a product of two means fails where the mean of products passes. It checks each row's coverage and height,
the premultiplied means, a row with no cover, and the normals turned into the view's basis. Set
`GRASS_CANOPY_TEST_CONTROL` to 2: the test's own copy of the fold divides each texel by its alpha before averaging, and
stage 3 fails. Set it back to 0.

**The table, on the GPU's real capture.** Run Horizon at Wind edge for a few frames and read its log:

```powershell
& ./Build/Artifacts/Release/SandboxGame/SandboxGame.exe --demo Horizon --horizon-view "Wind edge" --msaa 4 --frames 10
```

On frame 3 it prints one line:

```text
[INFO] Canopy table: coverage at 0 degrees 0.07303, rows with cover 3..12 (0 = the tips), card area 1.68387 m^2, layer height 0.70818 m, 2.25000 clumps per square metre
```

The coverage at 0 degrees is the share of the card's square a clump covers seen along the ground; times the card area
it is the 0.123 m² section 2 used (0.07303 × 1.68387). The rows with cover run from the tips' row down to the roots' row, and the layer
height is that span as a share of the clump's side. A line that never appears means the copy was never taken: the
request in `CoastalArea::Initialize` is missing, or `Generate` passes no frame slot.

**Nothing else changed.** The copy adds commands and changes no pixel. Capture Wind edge with the kept build and with
this one at a fixed clock, and compare:

```powershell
foreach ($run in @(@('..\SandboxGame-before-58\SandboxGame.exe', 'wind-edge-before-58'),
                   @('.\Build\Artifacts\Release\SandboxGame\SandboxGame.exe', 'wind-edge-58-4')))
{
    & $run[0] --demo Horizon --horizon-view "Wind edge" --msaa 4 --width 1920 --height 1080 --fixed-dt 0.016666667 `
        --frames 90 --sequence $run[1] --sequence-first 30 --sequence-last 90 --sequence-every 30
}
Get-FileHash wind-edge-before-58\*.bmp, wind-edge-58-4\*.bmp
```

The two are equal, byte for byte; the reference compared Wind edge at this section's code. Controls A and B of the attempt are run in a Debug build:

```powershell
& 'C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe' .\Build\Projects\PillowFort.sln /m /p:Configuration=Debug /p:Platform=x64 /t:SandboxGame
& ./Build/Artifacts/Debug/SandboxGame/SandboxGame.exe --demo Horizon --horizon-view "Wind edge" --msaa 4 --frames 10
```

With both barriers in place it prints the `VALIDATION-SETTINGS` notice and two `WARNING-Shader-OutputNotConsumed`,
the three lines the build before this chapter prints.

Next: handing the table to the terrain's shader.

## 5. The table and its block

The terrain's fragment shader will draw the canopy (section 7), so the table must reach it, with the settings that
say where the cards stand: the schedule, the reach and its fade, the switch, the island's habitat rules and the grass's
colours and light. The table never changes after the bake, but the settings do, any frame, from the panel. One block
holds both, written once a frame.

**One uniform block, at the island's set.** The terrain already binds the island's set, set 1, whose ten bindings are
the heightmap, the material map and the coast's
([Chapter 38, section 2](38-Ground-Materials.md#2-the-map-on-the-gpu-and-the-islands-set)). The block becomes its
binding 10. Two other homes were weighed. A second push range is closed: the terrain's 64-byte `TerrainDraw` is
embedded in the grass's 128-byte push constants, the guaranteed minimum, so the terrain's range cannot grow without
the grass's. A host-written buffer per frame in flight would need an island set per frame in flight, where today there
is one. A single buffer written with `vkCmdUpdateBuffer` between two barriers, inside the frame's own command buffer,
is [Chapter 39, section 9's](39-Plants.md#9-planted-by-the-gpu) pattern, which you have typed: the update happens in
the queue's order, so the one buffer serves both frames in flight.

**Every field is born here.** The block holds every field the canopy reads, with the whole chapter in mind, so later
sections change what goes into it and what the shader does with it, never its layout. Every member is a `vec4` or an
array of `vec4`, so std140
([Chapter 8, section 8](08-Resources-And-Descriptors.md#8-one-layout-two-languages)) lays it out exactly as C++ does,
with no padding word, and the `static_assert`s at the end prove it field by field: 61 `vec4`, 976 bytes. In
`Shaders/Horizon/`, beside `HorizonTypes.h`, create `GrassCanopyBlock.h`:

```cpp
///========================================================
/// @author Gary Yang
/// @brief Chapter 58: the grass canopy's uniform block, shared by the terrain's fragment shader and C++
/// @copyright (C) Gary 2026
///========================================================
/* Shaders/Horizon/GrassCanopyBlock.h - Chapter 58 section 5: the block the terrain's fragment shader reads to draw the grass
   beyond the blades' reach. GLSL includes it as "GrassCanopyBlock.h", C++ as "Horizon/GrassCanopyBlock.h".

   One uniform buffer, binding 10 of the island's set (Terrain), written once a frame with vkCmdUpdateBuffer. Every member is a
   vec4 or an array of vec4, so the std140 layout (Chapter 8, section 8) and the C++ struct agree without a padding word.

   Every field is born here, with the whole of the chapter's reading in mind: later sections change what the CPU puts in them
   and what the shader does with them, never this layout. */
#ifndef PF_GRASS_CANOPY_BLOCK_H
#define PF_GRASS_CANOPY_BLOCK_H

#include "SharedShaderTypes.h"   /* the vec4 alias, on the C++ side */

#ifdef __cplusplus
    #include <cstddef>
    namespace pf::demos::horizon {
    using shared::vec4;
#endif

struct GrassCanopyBlock
{
    vec4 schedule;       /* x densityStart, y densityEnd (0 already resolved to maxDistance, as grassPopulationDensity does),
                            z farDensity, w fadeBand: the rank fade of grassPopulationCoverage */
    vec4 reach;          /* x maxDistance; y the cards' outer fade band, max(morphBand, 1) as grassPopulationReach resolves it;
                            z clumps per square metre; w the card area, metres squared */
    vec4 control;        /* x 1 when the canopy draws; y 1 for the cover view; z the grass's debug view; w the mean dryness,
                            clumpDryness / 2 */
    vec4 affinity;       /* the island push's groundAffinity: grass, soil, sand, the density kept under a closed canopy */
    vec4 conditions;     /* the island push's conditions: sea level; minimum and full dry height above it; minimum up normal */
    vec4 rootColor;      /* rgb linear; w roughness */
    vec4 tipColor;       /* rgb linear; w rootRoughness */
    vec4 dryColor;       /* rgb linear; w specular */
    vec4 light;          /* x translucency, y rootOcclusion, z highlightModel, w gustBrightness */
    vec4 coverage[2];    /* the capture's mean alpha by elevation row: [0] rows 0 to 3, [1] rows 4 to 6 (w unused) */
    vec4 rows[16];       /* per image row of the capture, 0 the blade tips: x c, y t (zw unused) */
    vec4 rowNormal[16];  /* xyz the row's mean normal in the view basis (right, up, toward the eye) */
    vec4 rowFace[16];    /* xyz the row's mean face normal, flipped toward the eye, same basis */
    vec4 wholeNormal;    /* xyz the whole clump's mean normal; w the whole clump's t */
    vec4 wholeFace;      /* xyz the whole clump's mean face normal; w the clump's covered height in metres (the table's layerHeight),
                            which section 7's march reads */
};

#ifdef __cplusplus
    static_assert(sizeof(GrassCanopyBlock) == 976, "GrassCanopyBlock layout drifted: 61 vec4.");
    static_assert(offsetof(GrassCanopyBlock, schedule) == 0, "GrassCanopyBlock alignment drifted.");
    static_assert(offsetof(GrassCanopyBlock, reach) == 16, "GrassCanopyBlock alignment drifted.");
    static_assert(offsetof(GrassCanopyBlock, control) == 32, "GrassCanopyBlock alignment drifted.");
    static_assert(offsetof(GrassCanopyBlock, affinity) == 48, "GrassCanopyBlock alignment drifted.");
    static_assert(offsetof(GrassCanopyBlock, conditions) == 64, "GrassCanopyBlock alignment drifted.");
    static_assert(offsetof(GrassCanopyBlock, rootColor) == 80, "GrassCanopyBlock alignment drifted.");
    static_assert(offsetof(GrassCanopyBlock, tipColor) == 96, "GrassCanopyBlock alignment drifted.");
    static_assert(offsetof(GrassCanopyBlock, dryColor) == 112, "GrassCanopyBlock alignment drifted.");
    static_assert(offsetof(GrassCanopyBlock, light) == 128, "GrassCanopyBlock alignment drifted.");
    static_assert(offsetof(GrassCanopyBlock, coverage) == 144, "GrassCanopyBlock alignment drifted.");
    static_assert(offsetof(GrassCanopyBlock, rows) == 176, "GrassCanopyBlock alignment drifted.");
    static_assert(offsetof(GrassCanopyBlock, rowNormal) == 432, "GrassCanopyBlock alignment drifted.");
    static_assert(offsetof(GrassCanopyBlock, rowFace) == 688, "GrassCanopyBlock alignment drifted.");
    static_assert(offsetof(GrassCanopyBlock, wholeNormal) == 944, "GrassCanopyBlock alignment drifted.");
    static_assert(offsetof(GrassCanopyBlock, wholeFace) == 960, "GrassCanopyBlock alignment drifted.");
    }
#endif

#endif
```

The block carries the island push's two habitat vectors, `affinity` and `conditions`, because the canopy must judge
habitat by the rule the grass's compute pass uses, `islandGrassDensity`
([Chapter 41, section 3](41-Grass-On-The-Island.md#3-habitat-before-density)), and those two are its inputs.

<a id="ch58-the-block"></a>

### Attempt CH58-the-block: which stage the second barrier names

Predict first: barrier (b), after the update, makes the block's bytes visible to whoever reads binding 10. Name its
destination stage and access. Then say what would change, in every Horizon frame, if it named `ISLAND_READERS`
instead, as the island's uploads do.

**Acceptance:** (b) names `FRAGMENT_SHADER` and `UNIFORM_READ`; (a) names `FRAGMENT_SHADER` to `CLEAR`, with no
access. Horizon's frames are unchanged, since nothing reads binding 10 yet. Section 7's control D, where a shader
first reads the binding, shows (b)'s stage is the right one. Stage 4 of the supplied test passes.

**Transfer:** the block is 976 bytes. `vkCmdUpdateBuffer` takes at most 65,536 bytes, in multiples of 4. If the table
grew past that limit, what would replace the update, and which of the two barriers would change?

<details>
<summary>Hint 1: who reads it</summary>

Section 7 declares the block in `Terrain.frag.glsl` only. Which stage runs that shader, and how does it read a
uniform block?

</details>

<details>
<summary>Hint 2: what a destination stage costs</summary>

A barrier's second scope holds back every command after it whose stages it names, until the first scope is done.
Which commands of a Horizon frame run vertex or compute stages after the update?

</details>

<details>
<summary>Hint 3: the island's rule</summary>

`ISLAND_READERS` exists for uploads made once, at load, where waiting costs nothing. This write happens every frame.

</details>

<details>
<summary>Worked solution: the fragment stage and the uniform read; every frame would wait</summary>

(b) is `CLEAR` / `TRANSFER_WRITE` to `FRAGMENT_SHADER` / `UNIFORM_READ`. With `ISLAND_READERS` as its destination,
every vertex shader and every compute dispatch recorded after the update, the terrain's rings, the grass's own passes,
the plants, the sea, would wait for it in every frame, the canopy off included, for a block none of them reads.

**Answer to the transfer.** A staging copy: the CPU writes the bytes to a host-visible buffer per frame in flight, and
`vkCmdCopyBuffer` moves them. (a) would then name the copy stage as its destination and (b) the copy stage as its
source, `COPY` / `TRANSFER_WRITE`; the fragment side stays.

</details>

**The two barriers name one stage.** `vkCmdUpdateBuffer` is, to synchronization, a transfer write in the clear stage:
the specification files it with the clear commands, and sync validation reports it as `SYNC_CLEAR_TRANSFER_WRITE`
(Chapter 39, section 9). Two barriers surround it.

- (a), before: last frame's terrain may still be reading the block. The slot's fence is the frame before last's, and
  nothing since names the clear stage as a destination, so the update must wait for those reads: a write after reads,
  an execution dependency only, from the fragment stage to the clear stage.
- (b), after: the update's write, made visible to the fragment shader's uniform reads.

Only the terrain's fragment shader reads binding 10, and only in the canopy's form of it, so both barriers name the
fragment stage and no other. The island set's own rule is wider: every binding is visible to `ISLAND_STAGES`, vertex,
fragment and compute, and every upload's last barrier waits for `ISLAND_READERS`, all three. The binding keeps the
rule's visibility, which costs nothing. The barriers do not: naming every stage that reads the island would hold every
vertex and compute stage of every Horizon frame behind this write, the canopy off included.

**`Terrain.h`.** Above `#include "Horizon/HorizonTypes.h"`, add:

```cpp
#include "Horizon/GrassCanopyBlock.h"   // Chapter 58 section 5: RecordCanopy
```

Below the declaration of `DrawConstants`, add:

```cpp
    // Chapter 58 section 5: writes the grass canopy's block (island set, binding 10) with vkCmdUpdateBuffer, outside any render pass.
    void                  RecordCanopy(VkCommandBuffer commandBuffer, const GrassCanopyBlock& block) const;
```

Below `vulkan_graphics::AllocatedBuffer m_coastalOceanParameters;`, add:

```cpp
    vulkan_graphics::AllocatedBuffer m_canopyBlock;   // Chapter 58 section 5: island set binding 10
```

**`Terrain.cpp`.** In `Shutdown`, below `destroyBuffer(m_context,m_coastalOceanParameters);`, add:

```cpp
    destroyBuffer(m_context, m_canopyBlock);                       // Chapter 58 section 5
```

`CreateIslandSet` makes the set. The buffer is host-visible only so it can start as zeros, and a zero block draws
nothing: its `control.x`, the switch, is 0 until the first update. In `CreateIslandSet`, below the `if` that checks
the coastal ocean parameters' `vmaFlushAllocation` and its closing brace, above
`std::array<VkDescriptorSetLayoutBinding, 10> bindings{};`, add:

```cpp
    // Chapter 58 section 5: binding 10, the grass canopy's block. Zeros, so nothing draws (control.x is 0) until the first
    // RecordCanopy; TRANSFER_DST because vkCmdUpdateBuffer writes it each frame.
    m_canopyBlock = createBuffer(m_context, sizeof(GrassCanopyBlock),
        VK_BUFFER_USAGE_UNIFORM_BUFFER_BIT | VK_BUFFER_USAGE_TRANSFER_DST_BIT, true);
    if (!m_canopyBlock.buffer || !m_canopyBlock.mapped)
    {
        return InitializationResult::failure("Grass canopy block allocation failed.");
    }
    std::memset(m_canopyBlock.mapped, 0, sizeof(GrassCanopyBlock));
    if (vmaFlushAllocation(m_context.allocator, m_canopyBlock.allocation, 0, VK_WHOLE_SIZE) != VK_SUCCESS)
    {
        return InitializationResult::failure("Grass canopy block flush failed.");
    }
```

Then the set grows by one binding. Replace `std::array<VkDescriptorSetLayoutBinding, 10> bindings{};` with:

```cpp
    std::array<VkDescriptorSetLayoutBinding, 11> bindings{};
```

In the loop below it, binding 9 was the only uniform buffer; replace the line
`binding == 9 ? VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER : VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER,` with:

```cpp
                binding >= 9 ? VK_DESCRIPTOR_TYPE_UNIFORM_BUFFER : VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER,
```

`createDescriptorSets` counts its pool from the bindings
([Chapter 20, section 4](20-Compute-Fundamentals.md#4-storage-images)), so the pool grows with them. Below
`const VkDescriptorBufferInfo parameters{m_coastalOceanParameters.buffer, 0, VK_WHOLE_SIZE};`, replace
`std::array<VkWriteDescriptorSet, 10> writes{};` with these two lines:

```cpp
    const VkDescriptorBufferInfo canopy{m_canopyBlock.buffer, 0, VK_WHOLE_SIZE};
    std::array<VkWriteDescriptorSet, 11> writes{};
```

and in the loop below it, replace `.pBufferInfo = binding == 9 ? &parameters : nullptr,` with:

```cpp
            .pBufferInfo = binding == 9 ? &parameters : binding == 10 ? &canopy : nullptr,
```

After the function `DrawConstants`, below its closing brace and the blank line after it, and above
`void Terrain::Record(`, add `RecordCanopy`, with a blank line below it:

```cpp
// Chapter 58 section 5: Chapter 39 section 9's pattern (Understory.cpp), for a uniform block. A clear-stage write is what
// vkCmdUpdateBuffer is to synchronization: the spec files it with the clear commands. Only the terrain's canopy fragment
// shader reads binding 10, so both barriers name the fragment stage and no other: naming every stage that reads the island
// set would order each vertex and compute stage of every Horizon frame behind the write, canopy off included.
void Terrain::RecordCanopy(VkCommandBuffer commandBuffer, const GrassCanopyBlock& block) const
{
    // (a) Last frame's terrain may still be reading this block in its fragment shader: this slot's fence is the frame
    //     before last's, and no barrier since names the clear stage as a destination, so the update waits for those reads
    //     here: a write after reads, an execution dependency only. Sync validation may stay silent without it at 4x MSAA
    //     with the shoreline's optics on: that pass's ALL_GRAPHICS barrier (Chapter 43) can be read as covering the clear
    //     stage, which the spec's ALL_GRAPHICS does not include. So this barrier is argued, not shown by a quiet layer.
    memoryBarrier(commandBuffer, VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_NONE, VK_PIPELINE_STAGE_2_CLEAR_BIT, VK_ACCESS_2_NONE);
    vkCmdUpdateBuffer(commandBuffer, m_canopyBlock.buffer, 0, sizeof(GrassCanopyBlock), &block);
    // (b) What the update wrote, visible to the fragment stage's uniform reads.
    memoryBarrier(commandBuffer, VK_PIPELINE_STAGE_2_CLEAR_BIT, VK_ACCESS_2_TRANSFER_WRITE_BIT,
                  VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_UNIFORM_READ_BIT);
}
```

Barrier (a)'s comment records something you will see in section 7: at 4x MSAA with the shoreline's optics on, their
`OpaqueInputs::Record` (`ShorelineOptics.cpp`) records a barrier on `ALL_GRAPHICS`, which the layer can read as reaching
the clear stage, so sync validation
may stay quiet without (a). The specification's `ALL_GRAPHICS` does not include the clear stage. The barrier is argued,
and section 7's control C shows it at 1x, where that pass does not run.

**`CoastalArea.h`.** The block is made from what `CoastalArea::Prepare` already has: the grass's packed parameters, the
island push and the table. A free function makes it, so the supplied test can call it without a device. Below
`static_assert(uint32_t(CoastalWaterView::Wetness)==COAST_VIEW_WETNESS);` and its blank line, add, with a blank line
below it:

```cpp
// Chapter 58 section 5: the terrain's canopy block from this frame's packed grass parameters (the colours already linear),
// the island push's habitat inputs and the folded capture. `draws` false gives the zero block, which draws nothing; `coverView` sets the cover view's flag, which only a drawing block carries. A free
// function so the supplied test can call it without a device.
GrassCanopyBlock makeGrassCanopyBlock(const grass::GrassParameters& packed, const grass::IslandGrassPush& push,
                                      const grass::GrassCanopyTable& table, bool coverView, bool draws);
```

**`CoastalArea.cpp`.** The function writes out two resolutions the grass kernel makes for itself: a `densityEnd` of 0
means the reach, as `grassPopulationDensity` reads it, and the cards' outer fade band is `max(morphBand, 1)`, as
`grassPopulationReach` reads it. The colours are already linear: `PackParameters` linearized them. Above
`CoastalArea::Prepare`, add, with a blank line below it:

```cpp
// Chapter 58 section 5. The two resolutions below are the grass kernel's own, written out: densityEnd as
// grassPopulationDensity resolves it, and the cards' outer fade band as grassPopulationReach does (GrassClumpSource.h).
GrassCanopyBlock makeGrassCanopyBlock(const grass::GrassParameters& packed, const grass::IslandGrassPush& push,
                                      const grass::GrassCanopyTable& table, bool coverView, bool draws)
{
    GrassCanopyBlock block{};
    if (!draws) { return block; }
    const float densityEnd = packed.densityEnd > 0.0f ? packed.densityEnd : packed.maxDistance;
    block.schedule = { packed.densityStart, densityEnd, packed.farDensity, packed.fadeBand };
    block.reach = { packed.maxDistance, std::max(packed.morphBand, 1.0f), table.clumpsPerSquareMetre, table.cardArea };
    block.control = { 1.0f, coverView ? 1.0f : 0.0f, float(packed.debugView), 0.5f * packed.clumpDryness };
    block.affinity = push.groundAffinity;
    block.conditions = push.conditions;
    block.rootColor = { packed.rootColor.x, packed.rootColor.y, packed.rootColor.z, packed.roughness };
    block.tipColor = { packed.tipColor.x, packed.tipColor.y, packed.tipColor.z, packed.rootRoughness };
    block.dryColor = { packed.dryColor.x, packed.dryColor.y, packed.dryColor.z, packed.specular };
    block.light = { packed.translucency, packed.rootOcclusion, float(packed.highlightModel), packed.gustBrightness };
    block.coverage[0] = { table.coverage[0], table.coverage[1], table.coverage[2], table.coverage[3] };
    block.coverage[1] = { table.coverage[4], table.coverage[5], table.coverage[6], 0.0f };
    for (size_t row = 0; row < table.c.size(); ++row)
    {
        block.rows[row] = { table.c[row], table.t[row], 0.0f, 0.0f };
        block.rowNormal[row] = glm::vec4(table.normal[row], 0.0f);
        block.rowFace[row] = glm::vec4(table.face[row], 0.0f);
    }
    block.wholeNormal = glm::vec4(table.wholeNormal, table.wholeT);
    block.wholeFace = glm::vec4(table.wholeFace, table.layerHeight);
    return block;
}
```

The block is written every frame, so the canopy never outlives its grass: with **Island grass** off it is all zeros
and draws nothing. In `Prepare`, below `m_timestamps.Write(frame.commandBuffer, slot, 0);`, add:

```cpp
    // Chapter 58 section 5: the canopy's block, every frame, so a canopy never outlives its grass; zeros until the grass is on.
    GrassCanopyBlock canopy{};
```

Inside the grass's block, below `m_grass.Generate(frame.commandBuffer, slot);`, add:

```cpp
        canopy = makeGrassCanopyBlock(parameters, push, m_grass.CanopyTable(), false, m_grass.CanopyTable().valid);
```

and below that block's closing brace, above `if (m_seaEnabled)`, add:

```cpp
    terrain.RecordCanopy(frame.commandBuffer, canopy);   // outside any render pass: Horizon begins the scene pass after Prepare
```

`vkCmdUpdateBuffer` may not be recorded inside a render pass. `Prepare` runs before Horizon begins its scene pass, and
it records the grass's compute work there already.

**`premake5.lua`.** From stage 4 the supplied test includes `CoastalArea.h`, which reaches the sea's ImGui panels. In
the `TutorialGrassCanopyTests` project, replace the line
`includedirs { "Vendor/GLFW/include" }   -- GrassField.h reaches GlfwWindow.h through Demo.h` with:

```lua
        -- GrassField.h reaches GlfwWindow.h through Demo.h; from stage 4 CoastalArea.h reaches the sea's ImGui panels
        includedirs { "Vendor/GLFW/include", "Vendor/ImGui", "Vendor/ImGui/backends" }
```

### Checkpoint

Raise the supplied test's stage. In `GrassCanopyTests.cpp`, replace the line that starts `#define PF_TEST_STAGE` with:

```cpp
#define PF_TEST_STAGE 4   // raised in each section of Chapter 58
```

`GrassCanopyBlock.h` is new and `premake5.lua` changed, so generate again, then build the game in Release and the test
in Debug, and run the test, with the commands of section 4's checkpoint.

```text
reach 42 m: 360 tiles, 404 examined
reach 120 m: 559 tiles, 624 examined
reach 160 m: 708 tiles, 809 examined
reach 200 m: 896 tiles, 1044 examined
elevation 45 deg, n 12: tau 2.29183, gaps 0.1004 measured, 0.101081 from the law
elevation 25 deg, n 1.5: tau 0.614356, gaps 0.54035 measured, 0.540989 from the law
elevation 8 deg, n 1: tau 1.35894, gaps 0.25803 measured, 0.256934 from the law
elevation 2 deg, n 0.5: tau 2.73456, gaps 0.06594 measured, 0.0649225 from the law
the share and the generator's mean coverage differ by at most 1.0122e-06
at 12 m the cards draw 1 of the clumps
at 20 m the cards draw 0.733333 of the clumps
at 30 m the cards draw 0.45 of the clumps
at 41 m the cards draw 0.00485272 of the clumps
layer height 0.885131 m
card area 1.68387 m^2, 2.25 clumps per square metre
PASS: grass canopy, stage 4 (68 checks)
```

Stage 4 calls `makeGrassCanopyBlock` on packed parameters, a push and a table it builds, and checks every field where
the shader will read it: the schedule with `densityEnd` resolved, the reach and its band, the switch, the cover view
only where the block draws, the colours and light terms, the coverage rows, and the layer height in `wholeFace.w`; and
the zero block where it does not draw.

Capture Wind edge with the kept build and this one, as in section 4's checkpoint: the frames are equal, byte for byte,
since no shader reads binding 10 yet (the reference compared Wind edge at this section's code). A Debug run at Wind edge prints the same three lines as before the chapter.

Next in this chapter: [Sections 6 and 7 — The canopy](GrassToTheHorizonCanopy.md).

