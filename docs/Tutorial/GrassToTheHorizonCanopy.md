# 58 — Grass to the Horizon, page 3: the canopy

**Chapter 58's pages:** [1. Sections 1 to 3 — How much ground a field hides](58-Grass-To-The-Horizon.md) · [2. Sections 4 and 5 — What the capture knows](GrassToTheHorizonBake.md) · **3. Sections 6 and 7 — The canopy** · [4. Sections 8 to 10 — How far the cards go](GrassToTheHorizonReach.md).

Page 2 read the clump capture back after the bake and folded it into a table on the CPU
([section 4](GrassToTheHorizonBake.md#4-reading-the-capture-back)), and handed the table and the grass's settings to
the terrain's shader in a uniform block at the island's binding 10, written every frame
([section 5](GrassToTheHorizonBake.md#5-the-table-and-its-block)). No shader reads the block yet, and every frame is
still the kept build's. The supplied test is at stage 4. Keep `..\SandboxGame-before-58`: both checkpoints on this page
compare with it. The prerequisites are the chapter's, listed in its [header](58-Grass-To-The-Horizon.md).

## 6. One grass light

The canopy stands for the grass, so it must be lit as the grass is: the sky's light around its normal, the sun through
the blades from behind, the highlight toward the tips, the root's shade. All of that is the second half of
`shadeGrass` in `GrassFragmentKernel.glsl`
([Chapter 53, section 6](53-Rolling-Wind.md#6-a-gust-you-can-see-from-far-away) last changed it). Copying it into the
terrain's shader would give two lights that drift apart the first time someone edits one. So the two must share one
text.

That half reads its terms from `grass.*`, the grass's own uniform block at set 1 of the grass's layout, which the
terrain's pipeline cannot bind: its set 1 is the island. The natural cure is a function, `grassLight(terms, surface,
sun)`, taking the six terms it reads as an argument. It was tried, and it is not what this section types. With the
same arithmetic and the terms passed in, the grass's compiled code changed shape: the compiler laid out the branches
differently, and on the reference's RTX 5090 the driver rounded one or two pixels by one code at Coast and Forest floor. Chapter 53's frames would then no longer be its frames, and every later check that compares grass frames with
an earlier build would have to explain the difference.

Chapter 56, [section 2](EverythingBendsATree.md#2-a-tree-bends-from-its-foot) met the same problem in the leaf shaders
and settled it with a rule: a shader that must keep its bytes stays an includer of an unchanged body. The lines move,
unchanged, into a file of their own, and `shadeGrass` includes them where they stood. The terrain includes the same lines inside
a function of its own (section 7), with local variables named as the lines read them, `grass` among them: a struct
of the six terms, filled from the block.

A body has no parameter list, so its header says what the includer must have in scope, and what the body defines in
the includer's scope, so that a name clash is found by reading, not by a compiler error far away.

**`GrassGust.glsl`.** The gust's two constants scale the albedo the canopy will average too, so they move into a file
both can include. In `Shaders/Grass/`, create `GrassGust.glsl`:

```glsl
// Shaders/Grass/GrassGust.glsl - Chapter 53: how a gust moves the grass's albedo. A file of its own so that the grass
// kernel and Horizon's terrain canopy read the same two numbers.
#ifndef PF_GRASS_GUST_GLSL
#define PF_GRASS_GUST_GLSL

const float GUST_DARKEN            = 0.14;   // how much a lull darkens the albedo at full Gust brightness
const float GUST_BRIGHTEN          = 0.22;   // how much a gust brightens it

#endif
```

In `GrassFragmentKernel.glsl`, replace the two lines that declare `GUST_DARKEN` and `GUST_BRIGHTEN`, below the comment
`// Wind shading constants (Chapter 53).`, with:

```glsl
#include "GrassGust.glsl"
```

**`GrassLightBody.glsl`.** In the same folder, create `GrassLightBody.glsl`. Below its header, the lines are the ones in
`shadeGrass` from `float viewDepth` to the closing brace of `if (lightHeader.sunIndex >= 0)`, byte for byte, with their
four-space indent:

```glsl
// Shaders/Grass/GrassLightBody.glsl - Chapter 58 section 6: the grass's light, as lines. It is a body, not a function:
// it is included inside shadeGrass (GrassFragmentKernel.glsl) and inside Horizon's terrain canopy (grassCanopy in
// Terrain.frag.glsl), so the grass's compiled code stays byte for byte what it was before the canopy shared it
// (Chapter 56's rule: a shader that must keep its bytes stays an includer of an unchanged body).
//
// The includer must have in scope, before the include:
//   locals:    albedo, occlusion, layLightGain, normal (rounded), faceNormal, toCamera, bladeT, filtered (bool),
//              normalLength, gradientVariance, far, gustSheenSun, worldPosition
//   globals:   frame (FrameBlock.glsl), lightHeader and lights (Lights.glsl), skyDiffuse (samplerCube, set 0 binding 10)
//   grass.*:   roughness, rootRoughness, specular, highlightModel, translucency, farHighlight (a variable named
//              `grass`, the grass's block or a struct with these six fields)
//   functions: lightIrradiance, atmosphereSunTransmission(position, toSun), sunShadow, grassFilteredAlpha,
//              schlickFresnel, ggxDistribution, smithGeometry, blinnPhongLobe; constants AMBIENT_SKY, MIN_ROUGHNESS,
//              PI, GRASS_HIGHLIGHT_GGX
// It defines, in the includer's scope: viewDepth, ambient, color, ambientColor, diffuseColor, throughColor,
// specularColor. Inside the sun's block it uses, and keeps there: L, irradiance, shadow, diffuse, through, halfway,
// NdotH, roughness, alpha, fresnel, highlight, NdotL, NdotV (the last two inside the GGX branch). The includer must
// not have those names in the same scope as the include.
    float viewDepth = -(frame.view * vec4(worldPosition, 1.0)).z;   // Chapter 17's cascade choice
    // Chapter 25 section 8: Chapter 24's switch - the sky's light around the normal, or Chapter 16's constant.
    vec3 ambient = frame.ambientMode == AMBIENT_SKY ? textureLod(skyDiffuse, normal, 0.0).rgb : lightHeader.ambient.rgb;
    vec3 color   = albedo * occlusion * ambient * layLightGain;
    vec3 ambientColor = color, diffuseColor = vec3(0), throughColor = vec3(0), specularColor = vec3(0);
    if (lightHeader.sunIndex >= 0)
    {
        vec3  L;
        vec3  irradiance = lightIrradiance(lights[lightHeader.sunIndex], worldPosition, L);
        irradiance *= atmosphereSunTransmission(worldPosition, L);
        float shadow     = sunShadow(worldPosition, faceNormal, viewDepth);

        float diffuse = max(dot(normal, L), 0.0);

        // Light through the blade: the sun on the face we cannot see, strongest
        // when we look toward the sun.
        float through = max(dot(-faceNormal, L), 0.0)
                      * (0.25 + 0.75 * pow(max(dot(-toCamera, L), 0.0), 4.0));

        // The highlight: Chapter 15's specular term, GGX or normalized Blinn-Phong, at the
        // rounded normal. One roughness drives both; every invocation takes the same branch.
        vec3  halfway   = normalize(L + toCamera);
        float NdotH     = max(dot(normal, halfway), 0.0);
        // Glossier toward the tip, so a bent blade's highlight is brightest there (rootRoughness: the root's roughness, as a multiple of the tip's).
        float roughness = max(grass.roughness * mix(grass.rootRoughness, 1.0, clamp(bladeT, 0.0, 1.0)), MIN_ROUGHNESS);
        float alpha     = filtered ? grassFilteredAlpha(roughness, normalLength, gradientVariance)
                                   : roughness * roughness;
        vec3  fresnel   = schlickFresnel(vec3(grass.specular), vec3(1.0), max(dot(toCamera, halfway), 0.0));
        vec3  highlight;
        if (grass.highlightModel == GRASS_HIGHLIGHT_GGX)
        {
            float NdotL = max(diffuse, 1e-4);
            float NdotV = max(dot(normal, toCamera), 1e-4);
            highlight = fresnel * ggxDistribution(NdotH, alpha) * smithGeometry(NdotV, NdotL, alpha)
                      / (4.0 * NdotL * NdotV);
        }
        else
        {
            highlight = fresnel * blinnPhongLobe(NdotH, alpha);   // comparison mapping: n = 2 / alpha^2 - 2; lobe shapes differ
        }
        highlight *= mix(1.0, grass.farHighlight, far);   // section 6: a pixel-sized blade's highlight is sparkle; farHighlight keeps a share of it

        diffuseColor = irradiance * shadow * albedo * occlusion / PI * diffuse * gustSheenSun * layLightGain;
        throughColor = irradiance * shadow * albedo * occlusion / PI * grass.translucency * through * gustSheenSun;
        specularColor = irradiance * shadow * highlight * diffuse;
        color += diffuseColor + throughColor + specularColor;
    }
```

Then in `shadeGrass`, replace those lines, from the one that starts `float viewDepth = -(frame.view` down to the closing
brace of `if (lightHeader.sunIndex >= 0)`, with the include, keeping the blank line above it and the one below:

```glsl
    #include "GrassLightBody.glsl"
```

<a id="ch58-one-light"></a>

### Attempt CH58-one-light: does the grass's SPIR-V change?

Predict first: after this section, do the grass's fragment shaders compile to the same SPIR-V as the kept build's, in
Release? In Debug? What could make them differ, although every line the compiler is given is the same?

**Acceptance:** every `.spv` file of the Release build equals the kept build's, byte for byte.

**Transfer:** the body's header lists 13 local names the includer must have in scope. Section 7's includer, the
terrain, has no blade, no `bladeT` along it and no lay. What should it put in each of those names so that the body
lights the mean of a field, not one blade?

<details>
<summary>Hint 1: what the compiler sees</summary>

`#include` pastes the file's text where the line stood. Compare that text with what `shadeGrass` held before.

</details>

<details>
<summary>Hint 2: what else is in a SPIR-V module</summary>

A Debug build compiles with `-g`, which records the source files and their lines in the module.

</details>

<details>
<summary>Hint 3: the constants</summary>

The two gust constants are now declared through an include at the same place in the file. Is their order the same?

</details>

<details>
<summary>Worked solution: the same in Release; Debug records the new file</summary>

In Release the compiler sees the same declarations and statements in the same order, so the modules are the same,
byte for byte. In Debug, `-g` records which file each line came from and its line number there, so the grass's
modules name `GrassLightBody.glsl` and differ; that is why the checkpoint compares the Release build. The two
constants are declared where they were, in the same order, through `GrassGust.glsl`.

**Answer to the transfer.** The terms of a steady field: `bladeT` the canopy's mean height up the blade, from the
capture's rows; `layLightGain` 1, since a lay is one blade's; `gustSheenSun` 1, the gust's sheen at its mean;
`occlusion` 1, because the root's shade is already in the averaged albedo; `far` 0 and `farHighlight` 1, so no share of
the highlight is lost to a pixel-sized blade; and `filtered` true, with `normalLength` the length of the mean normal,
so a field whose blades disagree has its highlight widened by exactly that. Section 7 sets each of them.

</details>

### Checkpoint

Two files are new, so generate again, then build the game in Release with the commands of
[section 4's checkpoint](GrassToTheHorizonBake.md#4-reading-the-capture-back), and compare every compiled shader with the kept build's:

```powershell
$before = Get-ChildItem -Recurse ..\SandboxGame-before-58\Shaders -Filter *.spv
$after  = Get-ChildItem -Recurse .\Build\Artifacts\Release\SandboxGame\Shaders -Filter *.spv
foreach ($file in $before)
{
    $relative = $file.FullName.Substring((Resolve-Path ..\SandboxGame-before-58\Shaders).Path.Length)
    $other = Join-Path .\Build\Artifacts\Release\SandboxGame\Shaders $relative
    if ((Get-FileHash $file.FullName).Hash -ne (Get-FileHash $other).Hash) { "differs: $relative" }
}
"$($before.Count) before, $($after.Count) after"
```

It prints no `differs:` line, and the two counts are equal. The supplied test stays at stage 4: this section adds no
CPU code.

Next: the canopy itself.

## 7. The canopy

Everything is in place: the law (section 2), the shares (section 3), the table (section 4), the block (section 5) and
the light (section 6). This section draws the canopy in the terrain's fragment shader, over the ground and under the
cards, which the terrain draws before.

**Where the law at one point fails.** Section 2's law, used at the pixel's own ground with the slope there, is the
obvious first form: τ = n N.y A m / (V · N). It was drawn first, and measured against a fair reference, real blades at
full density rendered eight times finer and averaged, at Coast on the reference's RTX 5090 (1920 × 1080, 4x MSAA,
frame 90, standing, the tile and its pixels in `REFERENCE.md`'s Chapter 58 section), with the canopy drawn for the
whole population and no cards, in a build only the reference has: where the reference's grass hid 88, 94 and 99 % of
the ground at 30, 40 and 50 to 80 m, the law at one point hid 65, 76 and 78 to 82 %. Its cover followed the dune
ripples, where the reference's lay evenly over them. The law is right; its inputs are taken at the wrong place. Where it
fails, and why, is the attempt below.

<a id="ch58-march"></a>

### Attempt CH58-march: where does the law fail?

Predict first. From **Aerial**, 1,000 m above Wind edge looking 55 degrees down at the island, and from Wind edge itself,
2.5 m up: in which view is the canopy's cover nearer 1, and does its colour lean toward the tips or the roots? Then
rolling ground: low ripples run across the view, 30 m in front of a 2 m eye. Which faces of the ripples does the eye see
most of? On those faces, does section 2's law at one point give more cover than the ground really has, or less, and
what did the ray cross just before it reached the face?

**Acceptance:** at Wind edge the canopy reaches the horizon. Tick **Show canopy cover** and look for black within 12 m,
where the cards draw the whole population, a grey that lightens with distance, and a lower cover from **Aerial**.
Stage 5 of the supplied test passes,
and its march cases print their errors. With the canopy off, Wind edge, Coast and Forest floor capture the kept build's
frames, byte for byte. Controls C and D fire in a Debug run.

**Transfer:** the march samples the height map the rings' vertices are built from, not the triangles drawn between
them, which a sample far along the ray has no ring for. Near the landing point the two can differ by about a tenth of a
metre. Which way would a sample that falls just under the drawn ground err, and why should a sample count only from the
ground up, so that this error never counts ground the ray did not cross?

<details>
<summary>Hint 1: the sine</summary>

From 1,000 m at 55 degrees, sin e is 0.82. From 2.5 m, at 100 m, it is 0.025.

</details>

<details>
<summary>Hint 2: what the top rows hold</summary>

The rows near the tips have the least alpha and the brightest, driest colour. A thick canopy gives them the weight.

</details>

<details>
<summary>Hint 3: the face and the crest</summary>

A face turned toward the eye meets the ray at a steeper angle than level ground does. Walk back along the ray from a
point on that face: how high above the ground is the ray where it passes over the crest in front?

</details>

<details>
<summary>Worked solution: grazing views cover more and show the tips; a face turned toward you is where one point fails</summary>

From Aerial the sine is 0.82, so even where no card is drawn τ = n A / 0.82 is under 0.35, a cover under 0.3: the
ground shows through. From Wind edge, past 60 m, the cover is near 1. The colour follows: seen from above, a thin
canopy weighs every row by its alpha, roots included; grazing, a thick canopy's weight goes to the top rows, the tips'
brighter, drier colour.

A low eye sees mostly the faces of the ripples turned toward it; the backs are foreshortened or hidden. On such a face
V · N is larger than V.y, so the law at one point gives a smaller τ than level ground would: less cover. But the ray
reached that face over the crest in front of it, and a ray at 3 degrees is still within the layer's 0.7 m of a crest
13 m before it lands. The grass on the crest hides the face, and the law at one point never sees the crest. The march
keeps level ground's length, H / V.y, on a face turned toward the camera, walks back over the crest and counts its
grass. That is why it never marches less than H / V.y: a shorter march on that face, the local slope's own length,
was tried and missed the crest.

Measured at Coast against the same reference, on the reference's RTX 5090 (1920 × 1080, 4x MSAA, frame 90, standing),
with the canopy drawn for the whole population in the reference's own build: at 30 to 40, 40 to 50, 50 to 60 and 60 to 70 m the reference hid 88, 93, 99 and 98 % of the ground, and the
march hides 72, 87, 95 and 97 %. In optical depth, the measure the law adds up, that is 60, 75, 60 and 92 % of the
reference's. Past 50 m the march is nearer; at 30 to 50 m it is still short, and section 10 says so.

**Answer to the transfer.** A sample that falls just under the drawn ground reads a height above itself and is under
the ground: `grassCanopyInLayer` returns false for a negative height and the sample counts nothing. The error is then a
missing tenth of a metre of path, not a counted piece of ground the ray never crossed, which would take its habitat from
somewhere else entirely.

</details>

> **Jump:** from a law at a point to a sum along a path. Hold this: the canopy has a height. On level ground with one
> habitat, the path through the layer is H / sin e long and meets n A m / H clumps a metre, and the two together give
> section 2's law, whatever H is. Everywhere else, the clumps the ray meets are the ones over the ground it passes,
> so the depth is summed along the path, with the habitat, the slope and the schedule of the ground under each piece.

**The march.** Start at the point the ray lands on and walk back toward the eye. The ray leaves the layer once it is
H above the ground under it, H being the layer's height the table measured (0.708 m on the reference). On level ground
the gap between ray and ground grows by V.y a metre, so the path is H / V.y. Where the ground climbs toward the eye, the
gap grows slower, by the ground's rise per metre, and the ray stays inside the layer longer. `grassCanopyMarchLength`
measures that climb two ways, at the landing point (dot(V, N) / N.y, from the slope there) and on average to the eye
(the eye's height above its own ground, over its distance), takes the slowest of the two and V.y, and so never marches
less than level ground's H / V.y. On a face turned toward the camera both are faster than V.y and H / V.y stands. The
march never runs past the eye: nothing behind it is seen.

The path is cut into `CANOPY_MARCH_STEPS`, 8 equal pieces. At the middle of each, the shader reads the ground's height
there; if the ray is inside the layer, between the ground and H above it, the piece adds n A m / H times its length,
with m the missing share of the ground under it: its habitat by the island's rule, its forest, its slope, and the
schedule's density at its distance from the camera. A piece under the ground adds nothing: that is ground the ray
never passed through. Eight pieces are a discretisation, not a law: the supplied test measures what it costs (stage 5
below).

The floor, `GRASS_CANOPY_MARCH_MIN_SINE`, 0.005, keeps the division finite where the ray does not climb at all; it caps
the march at H / 0.005, 142 m, only where the ray climbs slower than that and the eye is farther, and 142 m inside the
layer is an optical depth above 5 wherever a tenth of the habitat is missing. It is not a tuning.

> **Jump:** from a cover to a colour. Hold this: what a pixel shows of the canopy is not the whole clump's mean, but
> the layer a ray reaches first, and how deep it reaches depends on how much of the canopy lies in front of it.

**What the ray sees.** The capture's 16 rows run from the tips (row 0) to the roots. A ray entering the canopy from
above meets the rows in that order, and each row stops a share of what reaches it, in proportion to its mean alpha
`c`: the rows split the march's optical depth by `c`, and [Chapter 28, section 3's](28-Clouds.md#3-marching-a-ray)
front-to-back weights give each row exp(−above) × (1 − exp(−rowDepth)), where `above` is the depth of the rows before
it. The weights add up to the cover. A thin canopy (a small depth) weighs every row by its `c`; a thick one gives
nearly all the weight to the top rows. The canopy's colour is the weighted mean of each row's colour, root to tip,
times its root shade, as a blade has them at that height; its normal and face normal are the rows' means, turned from
the capture's view basis into the world.

**The light.** Section 6's body, included inside the canopy's function, lights that mean with the terms of a steady
field. It uses the sun's shadow at the canopy's face normal, as the grass does, so the ground's own shadow term,
`sunLit`, is not used by the canopy.

**A second compiled form.** All of this costs every terrain pixel a march of 8 samples, each a height, two reads of
the material map, the forest's five fetches and the slope's four. A frame without the canopy should pay nothing and
draw exactly what it drew before, as Chapter 56's frames without the wind did. So the canopy's lines go inside
`#ifdef PF_GRASS_CANOPY`, and the build compiles `Terrain.frag.glsl` twice: once without the macro, into the
`Terrain.frag.spv` it made before, byte for byte, and once with it, into `TerrainCanopy.frag.spv`. `Terrain` builds two
more pipelines with the second, for the rings and for the coastal bed, which shares the terrain's fragment shader, and
binds them only on a frame where the canopy draws.

The canopy draws only where it has something true to draw: the grass is on, the table has arrived, the switch is on,
the ground is drawn with its materials (the canopy sits in that branch of the shader, so **Ground materials** off still
gives [Chapter 37's](37-Objects-At-A-Distance.md) frame), and the grass's view is the shaded grass or one of its four
light views. In those four, the canopy paints its one term too. The other debug views are of the blades themselves,
so the canopy stays out of them, and Chapter 48's views keep their meaning.

**`GrassCanopy.h`.** The march's decisions go in the shared header, so the shader and the supplied test call the same
functions; the loop that reads the terrain stays in the shader, which alone has the terrain. First the constants. The
old guard keeps its name and value, and its comment says who still uses it. Replace the comment line
`// seen edge-on, where the optical depth would grow without bound.`, the second line of the comment above
`GRASS_CANOPY_MIN_SINE`, with:

```cpp
// seen edge-on, where the optical depth would grow without bound. The terrain's shader no longer uses it (section 7 marches
// the layer instead, with its own floor, below); section 2's per-pixel law and its test still do.
```

Below `#define GRASS_CANOPY_MIN_SINE 0.02f`, add, with a blank line above it:

```cpp
// Chapter 58 section 7: the march's floor on how fast the ray climbs away from the ground, and how many samples it takes. The
// floor keeps the division finite where the ray does not climb at all (a view at or below the horizontal, ground rising as
// fast as the ray); it caps the march at H / 0.005, 142 m at the capture's 0.708 m, only where the ray climbs slower than
// that and the eye is farther: 142 m inside the layer is an optical depth above 5 wherever a tenth of the habitat is missing.
// It is not a tuning. Each sample is a height, two reads of the ground map, the forest's five and the
// slope's four texel fetches, so a pixel's march is 8 of those and no more however grazing the ray.
#define GRASS_CANOPY_MARCH_MIN_SINE 0.005f
```

Below the `#endif` that closes the C++ and GLSL preamble, and its blank line, add, with a blank line below it:

```cpp
const int CANOPY_MARCH_STEPS = 8;
```

The law per metre of path. Below `grassCanopyOpticalDepth` and its blank line, add, with a blank line below it:

```cpp
// Chapter 58 section 7: the same law per metre of ray path inside the layer, for a march that crosses ground of changing
// habitat and slope. layerHeight is the layer's height in metres. On flat ground a ray at elevation e spends H / sin e
// metres in the layer, so summing this over that path gives grassCanopyOpticalDepth(n, A, m, 1, sin e) exactly: n * A * m / sin e.
PF_CANOPY_FUNCTION float grassCanopyExtinction(float clumpsPerSquareMetre, float projectedArea, float missingShare,
                                               float layerHeight)
{
    return clumpsPerSquareMetre * projectedArea * missingShare / max(layerHeight, 1e-4f);
}
```

The row weights and the march's three decisions. Below `grassCanopyMissingShare` and its blank line, add, with a blank
line below it:

```cpp
// Chapter 58 section 7: the share of the view that one layer of the canopy takes. Seen from above, front to back as Chapter 28
// section 3's march takes a cloud's slabs: of what reaches the layer, exp(-above) is left after the optical depth that lies
// in front of it, and the layer's own rowDepth stops 1 - exp(-rowDepth) of that. The layers' weights, summed down the
// canopy, are the cover grassCanopyCover gives for the whole depth.
PF_CANOPY_FUNCTION float grassCanopyRowWeight(float above, float rowDepth)
{
    return exp(-above) * (1.0f - exp(-rowDepth));
}

// Chapter 58 section 7: how far back along the view ray, from the ground it lands on toward the eye, the march looks. The ray
// leaves the layer once it is layerHeight above the ground under it, so the march must run for layerHeight over the rate at
// which the gap between ray and ground grows. On level ground that rate is viewUp (V.y, the sine of the view's elevation).
// Where the ground climbs toward the eye, the gap grows slower, by the ground's rise per metre, and the ray stays in the layer
// longer: two measures of that, and the march takes the slower of them and V.y, so it is never shorter than on level ground.
// slopeClimb is the rate at the hit point, dot(V, N) / N.y for the ground's normal N there; eyeAboveGround over eyeDistance
// is the rate on average all the way to the eye (the eye's height above the ground under it, over its distance from the hit
// point). On a face turned toward the camera both are faster than V.y and the level-ground length stands: a shorter march
// there would miss the crest in front of the face. Within the length the samples test the real terrain: under the ground
// counts nothing, inside the layer counts. The march never goes past the eye, because nothing behind it is seen.
PF_CANOPY_FUNCTION float grassCanopyMarchLength(float layerHeight, float viewUp, float slopeClimb, float eyeAboveGround,
                                                float eyeDistance)
{
    float averageClimb = eyeAboveGround / max(eyeDistance, 1e-3f);
    float climb        = min(viewUp, min(slopeClimb, averageClimb));
    float path         = layerHeight / max(climb, GRASS_CANOPY_MARCH_MIN_SINE);
    return min(path, eyeDistance);
}

// The distance along the ray, from the hit point, of sample i: the middle of the i-th of CANOPY_MARCH_STEPS equal pieces.
PF_CANOPY_FUNCTION float grassCanopyMarchAlong(float marchLength, int i)
{
    return (float(i) + 0.5f) * marchLength / float(CANOPY_MARCH_STEPS);
}

// Whether a sample is inside the layer: from the ground up to the layer's height. A sample under the ground is not: it is
// ground the ray never passed through, and its habitat is somebody else's.
PF_CANOPY_FUNCTION bool grassCanopyInLayer(float heightAboveGround, float layerHeight)
{
    return heightAboveGround >= 0.0f && heightAboveGround <= layerHeight;
}
```

**`GrassClumpSource.h`.** The canopy must place the population by the schedule the generator uses, but the terrain
has no `GrassParameters`. So the schedule's two curves are split onto their own numbers, and the two functions the
generator calls call them: one definition, two callers. Replace `grassPopulationDensity` and `grassPopulationReach`,
from `PF_CLUMP_FUNCTION float grassPopulationDensity` to the closing brace of `grassPopulationReach`, with:

```cpp
// Chapter 58 section 7: the schedule's two curves on their own numbers, so that the terrain, which has no GrassParameters, draws the
// population with the arithmetic the generator places it by. end and band are already resolved: the two functions below
// resolve them from the grass's block, and the terrain's canopy block carries them resolved.
PF_CLUMP_FUNCTION float grassScheduleDensity(float start, float end, float farDensity, float groundDistance)
{
    float along = clamp((groundDistance - start) / max(end - start, 0.01f), 0.0f, 1.0f);
    return mix(1.0f, clamp(farDensity, 0.0f, 1.0f), along);
}

PF_CLUMP_FUNCTION float grassScheduleReach(float maxDistance, float band, float groundDistance)
{
    return 1.0f - smoothstep(max(0.0f, maxDistance - band), maxDistance, groundDistance);
}

PF_CLUMP_FUNCTION float grassPopulationDensity(GrassParameters grass, float groundDistance)
{
    // The landscape population must not change when its representation reach changes.
    // Zero keeps earlier diagnostic callers' explicit legacy parameter contract.
    float end = grass.densityEnd > 0.0f ? grass.densityEnd : grass.maxDistance;
    return grassScheduleDensity(grass.densityStart, end, grass.farDensity, groundDistance);
}

PF_CLUMP_FUNCTION float grassPopulationReach(GrassParameters grass, float groundDistance)
{
    return grassScheduleReach(grass.maxDistance, max(grass.morphBand, 1.0f), groundDistance);
}
```

**`GrassCanopyLight.glsl`.** The light body reads six terms through a variable named `grass`. The terrain fills a
struct with them. In `Shaders/Horizon/`, create `GrassCanopyLight.glsl`:

```glsl
// Shaders/Horizon/GrassCanopyLight.glsl - Chapter 58 section 7: the six grass terms the light body reads from `grass.`.
// The grass kernel takes them from its own block; the terrain's canopy fills this struct from GrassCanopyBlock.
#ifndef PF_GRASS_CANOPY_LIGHT_GLSL
#define PF_GRASS_CANOPY_LIGHT_GLSL

struct GrassCanopyLight
{
    float roughness;       // the tip's perceptual roughness
    float rootRoughness;   // the root's roughness, as a multiple of the tip's
    float specular;        // the highlight's reflectance head-on: Chapter 15's F0
    float translucency;    // how much sunlight comes through a blade
    uint  highlightModel;  // GRASS_HIGHLIGHT_*
    float farHighlight;    // the share of the highlight kept where the grass fades into the ground
};

#endif
```

**`Terrain.frag.glsl`.** Every line the canopy adds goes inside `PF_GRASS_CANOPY`, so the shader without the macro is
the shader it was. First the includes: the grass's light needs `PreviewSurface.glsl`'s `PI` and specular terms, and
`Lights.glsl` for the sun, which Horizon's frame set provides at set 0, binding 1. Directly below
`#include "../Shoreline/ShorelineWetMaterial.glsl"`, with no blank line between, add:

```glsl
#ifdef PF_GRASS_CANOPY
// Chapter 58 section 7: the grass beyond the blades' reach, drawn by the ground. The grass's own light and population rules, so
// that the two cannot drift apart; PreviewSurface.glsl comes first because the light body needs its PI and specular terms.
#include "PreviewSurface.glsl"
#include "../Grass/GrassTypes.h"
#include "../Grass/GrassClumpSource.h"
#include "Lights.glsl"   // set 0 binding 1: lightHeader and lights, which the grass's light body reads
#include "../Grass/GrassGust.glsl"
#include "GrassCanopyLight.glsl"
#include "../Grass/GrassCanopy.h"
#include "../Grass/IslandGrassRules.h"
#include "GrassCanopyBlock.h"
#endif   // PF_GRASS_CANOPY
```

The block, at the island's binding 10. Below the line that declares `CoastalOceanBlock` at binding 9, add:

```glsl
#ifdef PF_GRASS_CANOPY
// Chapter 58 section 5: the canopy's table and settings, written every frame by Terrain::RecordCanopy; all zero when the grass is off.
layout(std140, set = 1, binding = 10) uniform GrassCanopyUniform { GrassCanopyBlock canopy; };
#endif   // PF_GRASS_CANOPY
```

The variant takes `PI` from `PreviewSurface.glsl`, the same float, and a second definition would not compile. Wrap the
line `const float PI          = 3.14159265;` so that it reads:

```glsl
#ifndef PF_GRASS_CANOPY
const float PI          = 3.14159265;
#endif   // the canopy variant takes PI from PreviewSurface.glsl (Chapter 58 section 7), the same float
```

**`grassCanopy`.** The function returns the ground's colour with the canopy over it, and the cover through `cover`.
In order: the area one clump shows at this view's elevation, interpolated between the capture's two nearest elevation
rows; the march, whose length and samples come from the header, reading at each sample the ground's height, its
material map (the grass, soil and sand weights, before steep rock takes its share, as the grass's compute pass is given
them), its forest and its slope; the visible layer from the tips down; the mean normal and face turned into the
world; and the light, with section 6's body. The map's reads take a level of detail from the piece's length, so a long
march reads the coarser levels, as the ground itself does far away; and a level, not a derivative, because the read sits
in a branch. Below `waterColor` and its blank line, add, with a blank line below it:

```glsl
#ifdef PF_GRASS_CANOPY
// Chapter 58 section 7: the grass the blades no longer draw, as the average of what a view ray through the missing clumps meets.
// `ground` is the ground's own colour here and `N` the ground's normal from the height map; the result is that colour with the
// canopy over it. `view` is the grass's debug
// view: a light view paints that one light term over the ground. The optical depth is marched: a grazing ray spends tens of
// metres in the grass layer, over crests and over other habitat, before it lands, so one sample at the hit point and the
// slope's sine there (section 2's law, which grassCanopyOpticalDepth keeps for the test) covers far too little. The march
// goes back along the ray from the hit point toward the eye, never past it, and adds grassCanopyExtinction wherever the ray is
// inside the layer, with the habitat, the forest, the slope and the schedule's density of the ground under that sample. The
// march's decisions (its length, where each sample sits, whether it is in the layer) are GrassCanopy.h's, which the supplied
// test calls too.
vec3 grassCanopy(vec3 ground, vec3 N, vec3 V, float sunLit, uint view, out float cover)
{
    cover = 0.0;
    float layerHeight = canopy.wholeFace.w;
    if (layerHeight <= 0.0) { return ground; }

    // The area one clump shows at this view's elevation: the capture's mean alpha between its two nearest elevation rows.
    float coordinate = grassClumpElevationCoordinate(degrees(asin(clamp(V.y, -1.0, 1.0))));
    int   row        = min(int(floor(coordinate)), 5);
    float rowA       = canopy.coverage[row / 4][row % 4];
    float rowB       = canopy.coverage[(row + 1) / 4][(row + 1) % 4];
    float area       = mix(rowA, rowB, coordinate - float(row)) * canopy.reach.w;

    // The march. The ray leaves the layer once the gap between it and the ground below reaches the layer's height; that gap
    // grows at V.y on level ground and slower where the ground climbs toward the eye, measured at the hit point (the normal)
    // and on average to the eye (the eye's height above its own ground). GrassCanopy.h takes the slowest, never shorter than
    // level ground's H / V.y, bounded by the distance to the eye; the samples sit at the middle of equal pieces of it and test
    // the real ground. The map's lookups use the piece's length as their footprint, so a long march reads the coarser levels,
    // as the ground itself does far away.
    bool  seaDrawn    = (terrain.flags & TERRAIN_EXTERNAL_WATER) == 0u;
    float eyeGround   = terrainHeight(frame.cameraPosition.xz);
    eyeGround         = seaDrawn ? max(eyeGround, 0.0) : eyeGround;
    float slopeClimb  = dot(V, N) / max(N.y, 1e-3);
    float marchLength = grassCanopyMarchLength(layerHeight, V.y, slopeClimb, frame.cameraPosition.y - eyeGround,
                                               distance(worldPosition, frame.cameraPosition.xyz));
    float pathStep    = marchLength / float(CANOPY_MARCH_STEPS);
    float mapTexel    = terrain.heightmap.x / float(textureSize(groundMap, 0).x);
    float mapLevel    = max(log2(pathStep / mapTexel), 0.0);
    float depth       = 0.0;
    for (int i = 0; i < CANOPY_MARCH_STEPS; ++i)
    {
        float along    = grassCanopyMarchAlong(marchLength, i);
        vec3  position = worldPosition + along * V;
        // The ground's height there, as the rings' vertices sample it (the vertex shader's sea flattening included), not the
        // drawn triangles between them, which a sample far along the ray has no ring for: near the hit point the two can differ
        // by about a tenth of a metre at most (estimated from the 8 m noise octave), and a sample that falls under the height
        // counts nothing. The ray is inside the layer where it is no higher above that height than the layer's, and no lower.
        float height   = terrainHeight(position.xz);
        float drawn    = seaDrawn ? max(height, 0.0) : height;
        if (!grassCanopyInLayer(position.y - drawn, layerHeight)) { continue; }

        // The habitat's weights there, as the grass kernel is given them: before steep rock takes its share. The map's
        // first layer holds sand, grass, soil (GroundMaterials.glsl); a level of detail, not a derivative, because this
        // read sits in a branch.
        vec2  uv      = groundMapUv(position.xz, terrain.heightmap.x);
        vec3  first   = textureLod(groundMap, vec3(uv, 0.0), mapLevel).rgb;
        vec3  second  = textureLod(groundMap, vec3(uv, 1.0), mapLevel).rgb;
        float total   = max(first.r + first.g + first.b + second.r + second.g + second.b, 1e-6);
        vec4  habitat = vec4(first.g, first.b, first.r, 0.0) / total;   // grass, soil, sand

        float forestHere = forestDensity(heightmap, terrain.heightmap, position.xz);
        float slope      = groundSlope(heightmap, terrain.heightmap, position.xz);
        float up         = inversesqrt(1.0 + slope * slope);   // the normal's y of a slope that steep

        float distanceHere = distance(position.xz, frame.cameraPosition.xz);
        float density = grassScheduleDensity(canopy.schedule.x, canopy.schedule.y, canopy.schedule.z, distanceHere)
                      * grassScheduleReach(canopy.reach.x, canopy.reach.y, distanceHere);
        float habitatShare = islandGrassDensity(habitat, drawn, up, forestHere, canopy.affinity, canopy.conditions);
        float missing = grassCanopyMissingShare(habitatShare, density, canopy.schedule.w);
        depth += grassCanopyExtinction(canopy.reach.z, area, missing, layerHeight) * pathStep;
    }
    cover = grassCanopyCover(depth);
    if (depth <= 0.0) { return ground; }

    // The visible layer: from the tips down, each image row of the capture takes its share of the optical depth in
    // proportion to its mean alpha, and the view reaches it through what lies above. The weights sum to the cover.
    float sumC = 0.0;
    for (int r = 0; r < 16; ++r) { sumC += canopy.rows[r].x; }
    sumC = max(sumC, 1e-6);
    vec3  meanAlbedo = vec3(0.0), meanNormal = vec3(0.0), meanFace = vec3(0.0);
    float meanT      = 0.0, sumW = 0.0, above = 0.0;
    vec3  tip        = mix(canopy.tipColor.rgb, canopy.dryColor.rgb, canopy.control.w);
    // The gust is 0.5 at the steady lean (the kernel's albedo *= mix(...bladeData.y...) line in GrassFragmentKernel.glsl), so its mean
    // in a steady field is the factor at 0.5.
    const float GRASS_MEAN_GUST = 0.5;
    float gust = mix(1.0 - GUST_DARKEN * canopy.light.w, 1.0 + GUST_BRIGHTEN * canopy.light.w, GRASS_MEAN_GUST);
    for (int r = 0; r < 16; ++r)
    {
        float rowDepth = depth * canopy.rows[r].x / sumC;
        float weight   = grassCanopyRowWeight(above, rowDepth);
        above += rowDepth;
        float t = canopy.rows[r].y;
        // The row's colour times its root shade, as a blade has them at height t. The product is what is averaged, since
        // the light multiplies the two together.
        meanAlbedo += weight * mix(canopy.rootColor.rgb, tip, t) * gust * mix(canopy.light.y, 1.0, t);
        meanNormal += weight * canopy.rowNormal[r].xyz;
        meanFace   += weight * canopy.rowFace[r].xyz;
        meanT      += weight * t;
        sumW       += weight;
    }
    sumW = max(sumW, 1e-9);
    meanAlbedo /= sumW;
    meanNormal /= sumW;
    meanFace   /= sumW;
    meanT      /= sumW;

    // The capture's normals are in the view's basis (right, up, toward the eye): up is the world's, toward the eye is the
    // view's horizontal part.
    vec3 toward = dot(V.xz, V.xz) > 1e-8 ? normalize(vec3(V.x, 0.0, V.z)) : vec3(0.0, 0.0, 1.0);
    vec3 right  = cross(vec3(0.0, 1.0, 0.0), toward);
    vec3 normal = normalize(meanNormal.x * right + meanNormal.y * vec3(0.0, 1.0, 0.0) + meanNormal.z * toward + vec3(1e-6));
    vec3 face   = normalize(meanFace.x * right + meanFace.y * vec3(0.0, 1.0, 0.0) + meanFace.z * toward + vec3(1e-6));

    // Chapter 58 section 6's light, with the terms of a field in a steady wind, which is what its mean is: no share of the
    // highlight is lost (farHighlight 1, far 0), the blades' lay adds no light and the gust's sheen is its mean, 1. The
    // mean normal is shorter than one where the blades disagree, and the filtered width widens the highlight by exactly
    // that.
    GrassCanopyLight grass;
    grass.roughness      = canopy.rootColor.w;
    grass.rootRoughness  = canopy.tipColor.w;
    grass.specular       = canopy.dryColor.w;
    grass.translucency   = canopy.light.x;
    grass.highlightModel = uint(canopy.light.z);
    grass.farHighlight   = 1.0;

    // The names the grass's light body reads (GrassLightBody.glsl lists them): the sun's shadow is the body's own, from the
    // blade's face normal, as the grass draws it, so `sunLit` (the ground's shadow) is not used here.
    vec3  albedo           = meanAlbedo;
    float occlusion        = 1.0;
    float layLightGain     = 1.0;
    float gustSheenSun     = 1.0;
    vec3  faceNormal       = face;
    vec3  toCamera         = V;
    float bladeT           = meanT;
    bool  filtered         = true;
    float normalLength     = clamp(length(meanNormal), 0.0, 1.0);
    float gradientVariance = 0.0;
    float far              = 0.0;
    #include "../Grass/GrassLightBody.glsl"

    vec3 lit = color;
    if (view >= GRASS_VIEW_AMBIENT && view <= GRASS_VIEW_SPECULAR)
    {
        lit = view == GRASS_VIEW_AMBIENT ? ambientColor : view == GRASS_VIEW_DIFFUSE ? diffuseColor
            : view == GRASS_VIEW_THROUGH ? throughColor : specularColor;
    }
    return mix(ground, lit, cover);
}
#endif   // PF_GRASS_CANOPY
```

In `main`, the canopy keeps whether it drew and what it hid, for the cover view. Below `vec3  color;`, add:

```glsl
#ifdef PF_GRASS_CANOPY
    bool  canopyDrew  = false;   // Chapter 58 section 7: whether the canopy took part, and the share of the ground it hid
    float canopyCover = 0.0;
#endif
```

It draws over the material branch's colour, before Chapter 43's wet sand darkens it. Below the line
`color = albedo * lightAt(shading, sunLit, worldPosition);`, inside the material branch, add:

```glsl
#ifdef PF_GRASS_CANOPY

            // Chapter 58 section 7: the grass the blades no longer draw, over this ground. Only the shaded grass, and the
            // four light views of it, reach the terrain: the other views are of the blades themselves.
            uint canopyView = uint(canopy.control.z);
            if (canopy.control.x > 0.5 && (canopyView == GRASS_VIEW_SHADED
                || (canopyView >= GRASS_VIEW_AMBIENT && canopyView <= GRASS_VIEW_SPECULAR)))
            {
                color = grassCanopy(color, N, V, sunLit, canopyView, canopyCover);
                canopyDrew = true;
            }
#endif
```

The cover view paints over every view above it. Below the closing brace of the block that draws the shoreline's
diagnostic views, above the comment that starts `// Section 1: dark lines along every cell edge`, add:

```glsl
#ifdef PF_GRASS_CANOPY
    // Chapter 58 section 7: the canopy's cover as grey, over whatever the views above drew, unhazed as they are.
    if (canopyDrew && canopy.control.y > 0.5)
    {
        color = vec3(canopyCover);
    }
#endif
```

**`premake5.lua`.** One source, two shaders: a table names the files compiled a second time, the macro and the second
output's path. Below the two comment lines that start `-- Tracked custom-build inputs keep a shader-only edit`, above
`local function configureShaderBuilds()`, add, with a blank line below it:

```lua
-- Chapter 58 section 7: one source, two shaders. A file listed here is compiled a second time with a macro defined, so the
-- shader without the macro keeps the bytes it had (Chapter 56's rule) and the variant needs no copy of the source.
local shaderVariants = {
    ["Shaders/Horizon/Terrain.frag.glsl"] = { { path = "Horizon/TerrainCanopy.frag", define = "PF_GRASS_CANOPY" } },
}
```

Each variant is an output of its source's custom build step, so MSBuild knows to build it. Below
`buildoutputs { output }`, add:

```lua
            for _, variant in ipairs(shaderVariants[file] or {}) do
                buildoutputs { "%{cfg.targetdir}/Shaders/" .. variant.path .. ".spv" }
            end
```

Then each configuration's command list gains the variant's `glslc` line. Replace the eight lines from
`filter { "files:" .. file, "configurations:" .. configuration }` to the `}` that closes `buildcommands`, inside the
loop over the configurations, with:

```lua
                local function compile(defines, target)
                    return '"$(VULKAN_SDK)/Bin/glslc.exe" -fshader-stage=' .. stage ..
                        ' --target-env=vulkan1.3 ' .. flags .. limits .. defines ..
                        ' -I "%{wks.location}/../../Shaders/Include"' ..
                        ' "%{wks.location}/../../Shaders/' .. path .. '.glsl" -o "' .. target .. '" || exit /b 1'
                end
                local commands = { '{MKDIR} "%{cfg.targetdir}/Shaders/' .. folder .. '"', compile("", output) }
                for _, variant in ipairs(shaderVariants[file] or {}) do
                    table.insert(commands, compile(" -D" .. variant.define, "%{cfg.targetdir}/Shaders/" .. variant.path .. ".spv"))
                end
                filter { "files:" .. file, "configurations:" .. configuration }
                    buildcommands(commands)
```

**`Terrain.h`.** `Record` learns which shader to draw with. Replace the comment above `Record` and its declaration,
from `// Inside the scene pass, after the clear to depth 0:` to the line that ends `bool skyOn) const;`, with:

```cpp
    // Inside the scene pass, after the clear to depth 0: every ring in one draw, centred on `ringCenter`. Chapter 58 section 7:
    // `canopy` draws them with the shader that has the grass canopy; off, the terrain's own shader draws, as before the chapter.
    void Record(VkCommandBuffer commandBuffer, const vulkan_graphics::SceneRenderer& sceneRenderer,
                uint32_t frameIndex, const TerrainSettings& settings, glm::vec2 ringCenter, bool skyOn, bool canopy) const;
    // Chapter 58 section 7: whether the ground is drawn with its materials, the test behind the shader's TERRAIN_GROUND: the
    // setting asks for it and the map was loaded. The canopy sits in that branch of the shader.
    bool GroundMaterialsDrawn(const TerrainSettings& settings) const { return m_materials.MapSize() > 0 && settings.groundMaterials; }
```

Below `VkPipeline       m_pipeline = VK_NULL_HANDLE;`, add:

```cpp
    VkPipeline       m_canopyPipeline = VK_NULL_HANDLE;   // Chapter 58 section 7: the same state, TerrainCanopy.frag.spv
    VkPipeline       m_coastalBedCanopyPipeline = VK_NULL_HANDLE;   // and the coastal bed's, which shares the fragment shader
```

**`Terrain.cpp`.** In `Shutdown`, below `vkDestroyPipeline(device, m_pipeline, nullptr);                // section 1`,
add:

```cpp
    vkDestroyPipeline(device, m_canopyPipeline, nullptr);          // Chapter 58 section 7
    vkDestroyPipeline(device, m_coastalBedCanopyPipeline, nullptr);
```

and below `m_pipeline              = VK_NULL_HANDLE;`, add:

```cpp
    m_canopyPipeline        = VK_NULL_HANDLE;
    m_coastalBedCanopyPipeline = VK_NULL_HANDLE;
```

In `CreatePipeline`, the two canopy pipelines are copies of the terrain's and the coastal bed's descriptions with the
variant as the fragment shader. Below the `if` that checks `m_pipeline` and its closing brace, add:

```cpp
    // Chapter 58 section 7: the terrain's shader with the canopy, for the frames that draw it; everything else is the same.
    auto canopyDesc = desc;
    canopyDesc.fragmentShader = "Horizon/TerrainCanopy.frag.spv";
    m_canopyPipeline = createGraphicsPipeline(m_context.device, m_pipelineCache, canopyDesc);
    if (m_canopyPipeline == VK_NULL_HANDLE)
    {
        return InitializationResult::failure("Creating the terrain's canopy pipeline failed.");
    }
```

and below the line that checks `m_coastalBedPipeline`, above `return InitializationResult::success();`, add:

```cpp
    // The coastal bed draws with the terrain's fragment shader too, so its canopy frames need the variant as well.
    coastalDesc.fragmentShader = "Horizon/TerrainCanopy.frag.spv";
    m_coastalBedCanopyPipeline = createGraphicsPipeline(m_context.device, m_pipelineCache, coastalDesc);
    if (!m_coastalBedCanopyPipeline) { return InitializationResult::failure("Creating the stable coastal bed's canopy pipeline failed."); }
```

`DrawConstants` sets the shader's `TERRAIN_GROUND` flag by a test that `CoastalArea` must share. Replace
`const bool ground = m_materials.MapSize() > 0 && settings.groundMaterials;` with:

```cpp
    const bool ground = GroundMaterialsDrawn(settings);   // Chapter 58 section 7: one test, which CanopyDraws shares
```

Replace `Record`'s signature, its first two lines, with:

```cpp
void Terrain::Record(VkCommandBuffer commandBuffer, const SceneRenderer& sceneRenderer, uint32_t frameIndex,
                     const TerrainSettings& settings, glm::vec2 ringCenter, bool skyOn, bool canopy) const
```

and in it, replace `vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, m_pipeline);` with:

```cpp
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, canopy ? m_canopyPipeline : m_pipeline);
```

and, inside `if (settings.stableCoast)`, replace
`vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, m_coastalBedPipeline);` with:

```cpp
        vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, canopy ? m_coastalBedCanopyPipeline : m_coastalBedPipeline);
```

**`CoastalArea.h`.** The switch, the cover view, and the one test that decides whether the canopy draws. First the free
function's comment, which section 5 wrote before the cover view had a switch: replace its three lines, from the
one that starts `// Chapter 58 section 5: the terrain's canopy block` to the one that ends `without a device.`, with:

```cpp
// Chapter 58 section 5: the terrain's canopy block from this frame's packed grass parameters (the colours already linear),
// the island push's habitat inputs and the folded capture. `draws` false gives the zero block, which draws nothing. A free
// function so the supplied test can call it without a device. `coverView` asks the shader to paint the cover as grey; the
// block carries it only where the canopy draws.
```

Below `void SetGrassEnabled(bool enabled) { m_grassEnabled = enabled; }`, add:

```cpp
    void SetGrassCanopy(bool enabled) { m_canopy = enabled; }              // Chapter 58 section 7
    void SetGrassCanopyView(bool enabled) { m_canopyView = enabled; }
```

Below `bool GrassEnabled() const { return m_grassEnabled; }`, add:

```cpp
    // Chapter 58 section 7: whether the terrain's canopy shader draws anything this frame, and so whether it is bound at all:
    // the grass is on, its table is folded, the canopy switch is on, the grass's debug view is the shaded grass or one of
    // the four light views, and the ground is drawn with the materials (`groundDrawn`, Terrain::GroundMaterialsDrawn: the
    // setting and a loaded map, the same test that sets the shader's flag). The cover view only adds to a canopy that draws,
    // so it asks for nothing alone. Otherwise the base shader draws, and the frame is the base's by construction.
    bool CanopyDraws(bool groundDrawn) const
    {
        const uint32_t view = static_cast<uint32_t>(m_grassSettings.debugView);
        const bool lightView = view == GRASS_VIEW_SHADED || (view >= GRASS_VIEW_AMBIENT && view <= GRASS_VIEW_SPECULAR);
        return groundDrawn && lightView && m_grassEnabled && m_grass.CanopyTable().valid && m_canopy;
    }
```

Below `bool m_grassEnabled = true;`, add:

```cpp
    bool m_canopy = true;        // Chapter 58 section 7: the grass beyond the blades' reach, drawn by the terrain
    bool m_canopyView = false;   // and its cover, as grey
```

**`CoastalArea.cpp`.** The block now carries the switch and the cover view. In `Prepare`, replace the line
`canopy = makeGrassCanopyBlock(parameters, push, m_grass.CanopyTable(), false, m_grass.CanopyTable().valid);` with:

```cpp
        canopy = makeGrassCanopyBlock(parameters, push, m_grass.CanopyTable(), m_canopyView,
            m_canopy && m_grass.CanopyTable().valid);
```

In `DrawControls`, below `debug_panels::checkbox("Island grass", &m_grassEnabled);`, add the two rows, through the
guarded widgets every panel uses:

```cpp
    debug_panels::checkbox("Grass canopy", &m_canopy);
    debug_panels::checkbox("Show canopy cover", &m_canopyView);
```

**`HorizonDemo.h`.** Below `void SetGrassDebugView(int view) { m_coastal.SetGrassDebugView(view); }`, add:

```cpp
    void SetGrassCanopy(bool enabled) { m_coastal.SetGrassCanopy(enabled); }               // --grass-canopy
    void SetGrassCanopyView(bool enabled) { m_coastal.SetGrassCanopyView(enabled); }       // --grass-canopy-view
```

**`HorizonDemo.cpp`.** The terrain draws with the canopy's shader only when the coast is active and `CanopyDraws` says
so. In `Record`, replace the line of the call `m_terrain.Record(commandBuffer, m_sceneRenderer, ...` below the
comment `// Chapter 36 section 1: the ground, after the clear to 0, and before the plates.` with:

```cpp
    m_terrain.Record(commandBuffer, m_sceneRenderer, frame.frameIndex, m_terrainSettings, m_ringCenter, skyOn,
                     m_coastalActive && m_coastal.CanopyDraws(m_terrain.GroundMaterialsDrawn(m_terrainSettings)));   // Chapter 58 section 7: the canopy's shader only when the canopy draws
```

**`Main.cpp`.** Two switches, checked as `--coast-grass` is. In `LaunchSettings`, below
`bool                              coastGrass = true;`, add:

```cpp
    bool                              grassCanopy = true;       // Chapter 58 section 7: --grass-canopy 0|1
    bool                              grassCanopyView = false;  // --grass-canopy-view 0|1
```

In `parseSettings`, below the block that reads `--coast-grass`, `--coast-sea` and `--coast-flow` and its closing
brace, add:

```cpp
        else if (key == "--grass-canopy" || key == "--grass-canopy-view")
        {
            settings.coastValuesValid &= value == "0" || value == "1";
            (key == "--grass-canopy" ? settings.grassCanopy : settings.grassCanopyView) = value == "1";
        }
```

In `main`, replace the line `Log::error("--coast-grass, --coast-sea and --coast-flow must be 0 or 1.");` with:

```cpp
        Log::error("--coast-grass, --coast-sea, --coast-flow, --grass-canopy and --grass-canopy-view must be 0 or 1.");
```

and below `horizonDemo.SetCoastalGrassEnabled(settings.coastGrass);`, add:

```cpp
    horizonDemo.SetGrassCanopy(settings.grassCanopy);
    horizonDemo.SetGrassCanopyView(settings.grassCanopyView);
```

### Checkpoint

Raise the supplied test's stage. In `GrassCanopyTests.cpp`, replace the line that starts `#define PF_TEST_STAGE` with:

```cpp
#define PF_TEST_STAGE 5   // raised in each section of Chapter 58
```

Two files are new and `premake5.lua` changed, so generate again; build the game in Release and the test in Debug, and
run the test, with the commands of [section 4's checkpoint](GrassToTheHorizonBake.md#4-reading-the-capture-back).
Check that `Build\Artifacts\Release\SandboxGame\Shaders\Horizon\TerrainCanopy.frag.spv` exists beside
`Terrain.frag.spv`.

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
march error against 1024 samples (the shader's 8 and 32):
  e 1 deg, the slope facing the camera, a habitat step at 40 %: depth 0.530796, 8 samples 24.7059 %, 32 samples 5.88235 %
  e 2 deg, the slope facing the camera, a habitat step at 40 %: depth 0.45593, 8 samples 12.3288 %, 32 samples 1.36986 %
  e 5 deg, the slope facing the camera, a habitat step at 40 %: depth 0.511436, 8 samples 9.53545 %, 32 samples 2.20049 %
ground falling away from the eye (an eye 2 m above it): the march's share of the whole ray's depth
  1.1 deg: 60 m 1 100 m 1 150 m 1 200 m 1
  2.9 deg: 60 m 1 100 m 1 150 m 1 200 m 1
  4.6 deg: 60 m 1 100 m 1 150 m 1 200 m 1
a convex break: the march takes 0.404179 of the whole ray's depth; run to the eye, 8 samples 1.01045, 32 samples 1.13675
PASS: grass canopy, stage 5 (89 checks)
```

Stage 5 tests the march through the header's own functions: on flat ground it gives section 2's law; it stops at the
eye; a sample under the ground counts nothing; a wall across the ray and a crest in front of a slope; a slope facing
the camera with a step in its habitat, where 8 samples err by 25, 12 and 10 % at 1, 2 and 5 degrees and 32 come within
6 %; ground falling away from an eye 2 m above it, at 1.1 to 4.6 degrees and 60 to 200 m, where the march takes the
whole of the ray's depth inside the layer against a sum of 200,000 pieces along the ray (level ground's H / V.y alone
took 0.11 to 0.63 of it there); the march never shorter than H / V.y; and a convex break, a ledge the ray grazes 110 m
out, reported, not passed or failed: the march takes 0.40 of that ray's depth, and running it to the eye reads 1.01 with
8 samples but 1.14 with 32, which is aliasing, not a fix. Then the row weights: they sum to the cover to 10⁻⁵, the top
row takes over 90 % at a depth of 50, and at a small depth they follow the rows' coverage to 10⁻³.

Two controls show stage 5 can fail. Set `GRASS_CANOPY_TEST_CONTROL` to 3: the test's own copy of the weights' loop
sums from the bottom row up, and stage 5 fails one check, `at lambda 50 the first covered row takes more than 90 % of
the cover`. Set it back to 0. The second breaks your header: in
`grassCanopyInLayer`, make the line `return heightAboveGround <= layerHeight;`, so a sample under the ground counts;
stage 5 fails three checks, the slope rising above the eye, the wall across the ray and the crest the ray crosses,
each of which puts samples under the ground. Put the line back.

**On screen.** Run Horizon at Wind edge and open **Coastal area**: **Grass canopy** is ticked, and the ground under
and past the cards shows grass to the horizon. Tick **Show canopy cover**: the shader paints the cover as grey, black
where the canopy hides nothing, white where it hides all the ground, and the cards are drawn over it as usual. By
section 2's law, look for black within 12 m and a grey that lightens with distance along the ground; from **Aerial**,
a darker grey. (The reference did not capture the cover view on this chapter's code; it is a diagnostic for your
eye.) Untick **Grass canopy**: section 1's flat ground is back past the cards.

Then the canopy off, against the kept build, at three views, with the frames section 4 compared:

```powershell
foreach ($view in 'Wind edge', 'Coast', 'Forest floor')
{
    $name = $view -replace ' ', '-'
    & ..\SandboxGame-before-58\SandboxGame.exe --demo Horizon --horizon-view $view --msaa 4 --width 1920 --height 1080 `
        --fixed-dt 0.016666667 --frames 90 --sequence "$name-before-58" --sequence-first 30 --sequence-last 90 --sequence-every 30
    & .\Build\Artifacts\Release\SandboxGame\SandboxGame.exe --demo Horizon --horizon-view $view --msaa 4 --width 1920 --height 1080 `
        --fixed-dt 0.016666667 --frames 90 --sequence "$name-58-7" --sequence-first 30 --sequence-last 90 --sequence-every 30 --grass-canopy 0
}
Get-FileHash *-before-58\*.bmp, *-58-7\*.bmp | Sort-Object Path | Format-Table Hash, Path
```

Each view's three frames hash the same in both. With the canopy off the terrain binds the pipeline it bound before
the chapter, and the terrain's own module is the old one. Three grass modules do differ from the kept build's from
this section on, `GrassGenerate.comp`, `IslandGrassGenerate.comp` and `GrassShadow.frag`: by the order of two constant
declarations, from the schedule's curves split onto their own numbers (and from section 8 also by the band's
select). So the equal frames are a measurement, not a consequence: on the reference's RTX 5090 all five views of
the exit check (these three, Lone tree and the Viewpoint) were equal on the chapter's code before a last change to
the canopy's march, which does not run with the canopy off, and Coast and Wind edge again after it
([section 10](GrassToTheHorizonReach.md#10-what-chapter-58-does-not-do-yet-and-the-exit-check)). Run section 6's
`.spv` comparison again now and it prints those three `differs:` lines, and 139 before, 140 after: the new
`TerrainCanopy.frag.spv`.

**Controls C and D**, in a Debug build, where a shader first reads binding 10. Both barriers of
`Terrain::RecordCanopy` are now load-bearing.

- **D:** in barrier (b), change the destination stage `VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT` to
  `VK_PIPELINE_STAGE_2_VERTEX_SHADER_BIT`. A Debug run at Wind edge, `--msaa 4 --frames 60` (its command is below),
  prints ten
  `SYNC-HAZARD-READ-AFTER-WRITE` at `vkCmdDraw` (the layer stops repeating one message after ten): the fragment stage
  reads the buffer `vkCmdUpdateBuffer` wrote. Put it back.
- **C:** delete barrier (a), the first `memoryBarrier` in `RecordCanopy`, and run with `--msaa 1`. It prints ten
  `SYNC-HAZARD-WRITE-AFTER-READ` at `vkQueueSubmit2`, the update writing the block a `vkCmdDraw` of the frame before
  read, and one `SYNC-HAZARD-WRITE-AFTER-WRITE`. At `--msaa 4`, the chapter's runs, the same change is silent: section 5 said why,
  the shoreline's `ALL_GRAPHICS` barrier, which runs only above 1x. Put it back.

```powershell
& 'C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe' .\Build\Projects\PillowFort.sln /m /p:Configuration=Debug /p:Platform=x64 /t:SandboxGame
& ./Build/Artifacts/Debug/SandboxGame/SandboxGame.exe --demo Horizon --horizon-view "Wind edge" --msaa 4 --frames 60   # D
& ./Build/Artifacts/Debug/SandboxGame/SandboxGame.exe --demo Horizon --horizon-view "Wind edge" --msaa 1 --frames 60   # C
```

With both barriers in place, a Debug run at Wind edge at 4x prints only the `VALIDATION-SETTINGS` notice and
the two `WARNING-Shader-OutputNotConsumed` the build before the chapter prints.

Next in this chapter: [Sections 8 to 10 — How far the cards go](GrassToTheHorizonReach.md).

