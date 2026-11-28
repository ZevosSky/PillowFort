# 58 — Grass to the Horizon, page 4: how far the cards go

**Chapter 58's pages:** [1. Sections 1 to 3 — How much ground a field hides](58-Grass-To-The-Horizon.md) · [2. Sections 4 and 5 — What the capture knows](GrassToTheHorizonBake.md) · [3. Sections 6 and 7 — The canopy](GrassToTheHorizonCanopy.md) · **4. Sections 8 to 10 — How far the cards go**.

Page 3 shared the grass's light with the terrain as an included body
([section 6](GrassToTheHorizonCanopy.md#6-one-grass-light)) and drew the canopy in a second compiled form of the
terrain's fragment shader, marched through the grass layer and shaded from the tips down
([section 7](GrassToTheHorizonCanopy.md#7-the-canopy)). The canopy now reaches the horizon, but the cards still end at
42 m. The supplied test is at stage 5. Keep `..\SandboxGame-before-58`: the exit check compares with it. The
prerequisites are the chapter's, listed in its [header](58-Grass-To-The-Horizon.md).

## 8. The hand-over

At a 42 m reach an edge shows behind the last cards: the cards are 15 % of the population there, and their reach
fades them out over the last `max(morphBand, 1)` metres, 4 m. Section 3 made the cards' and the canopy's shares add
up exactly in its arithmetic, but the screen is not that arithmetic: far cards that overlap hide less than the law
says (section 10), and a card is textured and moves in the wind where the canopy is smooth and still. Two things move
that edge: how far the cards run, and over how many metres they fade.

The reach already has a setting and a flag (`--coast-grass-reach`). The fade has neither: it is the morph band, which
belongs to the blades' level of detail. So the cards get an outer fade band of their own, `reachFadeBand`, which
`grassPopulationReach` uses when it is above 0. At 0 it keeps the band it had, so every frame before this section is
unchanged with the band at 0.

**`GrassParameters` keeps its 720 bytes.** The band lives in the grass's parameter block, which the compute pass and
the kernels read. That block is asserted at 720 bytes, and `PlantWindTests` holds its packing byte for byte
([Chapter 56, section 1](56-Everything-Bends.md#1-a-front-is-a-fact-of-the-island)); the reflection lesson's rows pack
into it too. A free float, `padding5`, sits just before `clumpSize`, so the band takes its place: the block keeps its
size and its offsets, and a band of 0 packs the same bytes as the padding did.

**The default.** The program's defaults become a reach of 120 m and a card fade of 30 m: the cards fade out over the
last 30 m of their reach. The band is a number of metres, not a share of the reach; 30 m is a quarter of
120 m, chosen by hand. The pair was chosen on
2026-11-26 from the reference's RTX 5090 numbers, standing and walking (section 9), and it is provisional: it is to be
checked on the RTX 4060 Laptop, the guide's frame budget at 1080p, 4x MSAA and 60 fps, and may be lowered there. The
pair is set in `Main.cpp`, where the program's launch settings live; `CoastalArea`'s own constructor keeps 42 m and no
band, because the program always sets both.

<a id="ch58-hand-over"></a>

### Attempt CH58-hand-over: the canopy across the band

Predict first, at the default pair, 120 m and 30 m, at Wind edge with **Show canopy cover** ticked: how does the cover
change between 90 and 120 m, where the cards fade out? Then with `--grass-reach-fade 0`, where they fade over 4 m at
120 m: does the cover step there? Does the picture?

**Acceptance:** stage 6 of the supplied test passes, and `TutorialPlantWindTests` still holds Chapter 53's 720 bytes.
Then your own judgment, at a band of 0 and at 30 m: does the cover step where the cards end, and does the picture?

**Transfer:** the band is a number of metres. What would the default 30 m do at a 42 m reach, and what band would
you give that reach?

<details>
<summary>Hint 1: what the cover counts</summary>

The cover counts the cards' and the canopy's shares together, and they always make up the habitat (section 3's stage 2
walked the schedule every 0.25 m to show it). Which of the two changes in the band?

</details>

<details>
<summary>Hint 2: what the cover view does not show</summary>

**Show canopy cover** paints the canopy's cover. The cards are drawn over it as they always are. What does the cover
view show where a card stands?

</details>

<details>
<summary>Hint 3: a band at a short reach</summary>

The schedule falls to 0.15 at 42 m. A 30 m band at a 42 m reach starts fading the cards at 12 m.

</details>

<details>
<summary>Worked solution: the arithmetic has no step; the picture is for your eye</summary>

Between 90 and 120 m the reach factor falls smoothly from 1 to 0, so the density the cards draw falls with it, and
`grassCardShare` falls; the missing share, h (1 − s), rises by the same amount; the canopy's cover rises through the
band to its full value at 120 m. The total, cards plus canopy, does not change: it is the habitat's. With the band at 0
the same exchange happens over 4 m instead of 30, still with no step in the arithmetic. Whether the picture steps is
for your eye: at a 42 m reach an edge did show behind the last cards, read then as a step in the cover, since far
cards hide less than the law; at 120 m it was not recorded, so look for it at a band of 0 and at 30 m.

**Answer to the transfer.** At a 42 m reach a 30 m band would fade the cards from 12 m, through the whole of the
schedule's thinning, where they are the near field's texture. The band hides a change of texture, and the eye sees it
at a size on screen, which distance sets: a band about a quarter of the reach starts the fade well past the
full-density disc, so about 10 m at 42 m. The setting does not scale itself; set it with the reach.

</details>

**`GrassTypes.h`.** Replace the line `float padding5;         /* free: keeps clumpSize at 424 */` with:

```cpp
    float reachFadeBand;    /* Chapter 58 section 8: metres of the cards' outer fade; 0 keeps max(morphBand, 1); still keeps clumpSize at 424 */
```

**`GrassClumpSource.h`.** In `grassPopulationReach`, replace the line
`return grassScheduleReach(grass.maxDistance, max(grass.morphBand, 1.0f), groundDistance);` with:

```cpp
    // Chapter 58 section 8: reachFadeBand widens the cards' outer fade, and the canopy reads the same schedule (the terrain's block
    // carries the band resolved); zero keeps the band this function had before, max(morphBand, 1).
    float band = grass.reachFadeBand > 0.0f ? grass.reachFadeBand : max(grass.morphBand, 1.0f);
    return grassScheduleReach(grass.maxDistance, band, groundDistance);
```

**`GrassField.h`.** In `GrassSettings`, below `float     morphBand         = 4.0f;     // metres`, add:

```cpp
    float     reachFadeBand     = 0.0f;     // metres, Chapter 58 section 8: the cards' outer fade; 0 keeps max(morphBand, 1)
```

**`GrassField.cpp`.** `PackParameters` fills the block in its members' order. Below the line that sets `.gustScale`,
add:

```cpp
        .reachFadeBand   = settings.reachFadeBand,   // Chapter 58 section 8
```

**`CoastalArea.cpp`.** The canopy's block carries the band resolved, as `grassPopulationReach` resolves it, so the
canopy fades in exactly where the cards fade out. Replace the second line of the comment above
`makeGrassCanopyBlock`, the one that starts `// grassPopulationDensity resolves it, and the cards' outer fade band`,
with:

```cpp
// grassPopulationDensity resolves it, and the cards' outer fade band as grassPopulationReach does (GrassClumpSource.h; Chapter 58 section 8 adds reachFadeBand).
```

and in it, replace the line that sets `block.reach` with:

```cpp
    block.reach = { packed.maxDistance, packed.reachFadeBand > 0.0f ? packed.reachFadeBand : std::max(packed.morphBand, 1.0f), table.clumpsPerSquareMetre, table.cardArea };
```

**`GrassCanopyBlock.h`.** The block's comment on `reach` says how its band is resolved, which section 5 wrote before the
band had a setting. Replace its two lines, from `vec4 reach;` to `w the card area, metres squared */`, with:

```cpp
    vec4 reach;          /* x maxDistance; y the cards' outer fade band as grassPopulationReach resolves it: reachFadeBand,
                            or max(morphBand, 1) where that is 0 (Chapter 58 section 8); z clumps per square metre; w the
                            card area, metres squared */
```

The band is a row of Horizon's panel, not of the grass's wind settings: it belongs to this demo's hand-over. In
`DrawControls`, below `debug_panels::checkbox("Grass canopy", &m_canopy);`, add:

```cpp
    // Chapter 58 section 8: the cards' outer fade, widened so the canopy takes over smoothly; 0 keeps the morph band.
    debug_panels::sliderFloat("Card fade band", &m_grassSettings.reachFadeBand, 0.0f, 100.0f, "%.0f m", ImGuiSliderFlags_AlwaysClamp);
```

The slider clamps a typed value, and the guarded `sliderFloat` puts back a typed NaN
([Chapter 9, section 6](09-Demo-Harness.md#6-the-triangle-becomes-a-demo)), so the band is never outside 0 to 100 m.

**`CoastalArea.h`.** Below `void SetGrassReach(float reach) { m_grassSettings.maxDistance = reach; }`, add:

```cpp
    void SetGrassReachFade(float band) { m_grassSettings.reachFadeBand = band; }   // Chapter 58 section 8
```

**`HorizonDemo.h`.** Below `void SetGrassReach(float reach) { m_coastal.SetGrassReach(reach); }`, add:

```cpp
    void SetGrassReachFade(float band) { m_coastal.SetGrassReachFade(band); }   // --grass-reach-fade
```

**`Main.cpp`.** The default pair, marked provisional where you read it. In `LaunchSettings`, replace the line
`float                             coastGrassReach = 42.0f;` with:

```cpp
    float                             coastGrassReach = 120.0f;  // Chapter 58 section 8: the cards run to 120 m, provisional (Gary, 2026-11-26)
    float                             grassReachFade = 30.0f;    // and fade out over their last 30 m (0 keeps the morph band); both until the laptop session
```

`--grass-reach-fade` is read as the other grass numbers are. In `parseSettings`, replace the block that starts
`else if (key == "--grass-wind" || key == "--grass-geometry-pixels" || key == "--grass-proxy-pixels"`, from its first
line down to the line `: key == "--grass-sun-azimuth" ? settings.grassSunAzimuth : settings.coastGrassReach;`, with:

```cpp
        else if (key == "--grass-wind" || key == "--grass-geometry-pixels" || key == "--grass-proxy-pixels"
                 || key == "--grass-sun-elevation" || key == "--grass-sun-azimuth" || key == "--coast-grass-reach"
                 || key == "--grass-reach-fade")
        {
            float& target = key == "--grass-wind" ? settings.grassWind
                : key == "--grass-geometry-pixels" ? settings.grassGeometryPixels
                : key == "--grass-proxy-pixels" ? settings.grassProxyPixels
                : key == "--grass-sun-elevation" ? settings.grassSunElevation
                : key == "--grass-sun-azimuth" ? settings.grassSunAzimuth
                : key == "--coast-grass-reach" ? settings.coastGrassReach : settings.grassReachFade;
```

In `main`, the range check gains the band. Replace the lines from
`|| settings.coastGrassReach < 12 || settings.coastGrassReach > 200)` down to the `Log::error("Invalid grass options:`
line below it with:

```cpp
        || settings.coastGrassReach < 12 || settings.coastGrassReach > 200
        || settings.grassReachFade < 0 || settings.grassReachFade > 100)
    {
        Log::error("Invalid grass options: use finite key/value pairs; switches 0/1, surface legacy/filtered/blades, wind [0,1], proxy px [2,40], geometry px [proxy+1,80], sun elevation [1,90], azimuth [0,360], coast reach [12,200], reach fade [0,100], work span 1 or 4.");
```

and below `horizonDemo.SetGrassReach(settings.coastGrassReach);`, add:

```cpp
    horizonDemo.SetGrassReachFade(settings.grassReachFade);
```

### Checkpoint

Raise the supplied test's stage. In `GrassCanopyTests.cpp`, replace the line that starts `#define PF_TEST_STAGE` with:

```cpp
#define PF_TEST_STAGE 6   // raised in each section of Chapter 58
```

No file is new. Build the game in Release, and the supplied test and the two tests that hold the grass's parameter
block in Debug, and run them:

```powershell
& 'C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe' .\Build\Projects\PillowFort.sln /m /p:Configuration=Release /p:Platform=x64 /t:SandboxGame
if ($LASTEXITCODE -ne 0) { throw 'The game build failed.' }
& 'C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe' .\Build\Projects\PillowFort.sln /m:1 /nr:false /p:CL_MPCount=1 /p:UseMultiToolTask=true /p:MultiProcMaxCount=1 /p:EnforceProcessCountAcrossBuilds=true /p:Configuration=Debug /p:Platform=x64 '/t:TutorialGrassCanopyTests;TutorialPlantWindTests;TutorialSettingRowsTests'
if ($LASTEXITCODE -ne 0) { throw 'The test build failed.' }
foreach ($test in 'GrassCanopy', 'PlantWind', 'SettingRows')
{
    & ".\Build\Artifacts\Debug\Tutorial${test}Tests\Tutorial${test}Tests.exe"
    if ($LASTEXITCODE -ne 0) { throw "Tutorial${test}Tests failed." }
}
```

The supplied test prints what stage 5 printed, and ends:

```text
PASS: grass canopy, stage 6 (105 checks)
```

Stage 6 checks that a band of 0 is today's smoothstep exactly; that a 160 m reach with a 40 m band is 1 at 120 m, a half
at 140 m and 0 at 160 m; that the block carries the band as `grassPopulationReach` resolves it; that along that schedule
the cards and what is missing make up the habitat every 0.25 m; and the pair that ships, 120 m and 30 m: full to 90 m, a
half at 105 m, 0 at 120 m, the shares continuous. `PlantWindTests` and `SettingRowsTests` end with the `PASS:` lines
they printed before this section: a band of 0 packs Chapter 53's 720 bytes.

**On screen.** Run Horizon at Wind edge with the defaults, then the same with the cards as they were:

```powershell
& ./Build/Artifacts/Release/SandboxGame/SandboxGame.exe --demo Horizon --horizon-view "Wind edge" --msaa 4 --width 1920 --height 1080
& ./Build/Artifacts/Release/SandboxGame/SandboxGame.exe --demo Horizon --horizon-view "Wind edge" --msaa 4 --width 1920 --height 1080 --grass-canopy 0 --coast-grass-reach 42 --grass-reach-fade 0
```

![Two strips of Horizon at Wind edge, one above the other, frame 90 of a walk along the view. Above, as before this chapter: blades and cards in front, then flat ground under the oaks. Below, at the defaults: the same blades and cards, and past them the meadow under the oaks has short grass and a darker, grassier colour reaching back to the trees.](images/58-wind-edge-walk.png)

The picture is rows 440 to 759 of frame 90 of section 9's walk route from Wind edge, at a fixed clock, on the
reference's RTX 5090: above, with `--grass-canopy 0 --coast-grass-reach 42 --grass-reach-fade 0`; below, at the
defaults. Tick **Show canopy cover** and look along the ground through 90 to 120 m: stage 6 holds the shares
continuous there, so look for a grey with no ring where the cards end. Drag **Card fade band** to 0: the cards now end
over 4 m, and the cover still has no step; judge whether the cards' end shows as a line. (The reference recorded these
frames at the defaults only.)

Next: what the new default costs, standing and walking.

## 9. What it costs, standing and walking

The default reach was chosen from what it costs, and a reach costs more than it seems standing still. The grass is
generated anew each frame for wherever the camera is: the tiles around it are selected on the CPU, the clumps are
placed in a compute pass, and the cards are drawn from what survives. Standing, the same tiles come back every frame;
walking, the tiles at the edge of the reach change. A reach is measured both ways.

Horizon has camera routes for this kind of run (`--horizon-route`; `coast-walk` among them), each a
function of the time since the route began, so with a fixed clock two runs walk the same path. This section adds two
that start from whichever view is selected: `walk`, straight ahead along the view's heading at 3 m/s, at the view's
height above the ground and its pitch, and `turn`, a slow turn in place, 6 degrees a second. From Wind edge, the walk is
the path behind the pictures of section 8. Both need a ground view to start from, so the Viewpoint and the plates,
which are not views of the ground, refuse them.

**`HorizonDemo.h`.** The selected view, kept as `GoTo` takes it. Below `float m_routeTime = 0.0f;`, add, with no blank
line between:

```cpp
    // Chapter 58 section 9: the selected view as GoTo takes it, kept for the routes "walk" and "turn".
    struct StartView
    {
        glm::vec2 xz{ 0.0f };
        float     height = 0.0f;   // metres above the ground at xz
        float     yaw    = 0.0f;   // degrees
        float     pitch  = 0.0f;   // degrees
    };
    StartView m_startView;
    bool      m_haveStartView = false;
```

**`HorizonDemo.cpp`.** Below `constexpr float     VIEW_PITCH = glm::radians(-10.0f);` and its blank line, add, with a
blank line below it:

```cpp
// Chapter 58 section 9: the rates of the routes "walk" and "turn".
constexpr float     WALK_SPEED = 3.0f;   // metres a second: an easy walking pace
constexpr float     TURN_RATE  = 6.0f;   // degrees a second: a slow look around, 60 degrees in 10 s
```

In `Update`, the routes are an `if` chain on `m_route`. Above `else if (m_route == "coast-walk")`, add:

```cpp
        // Chapter 58 section 9: two routes from whatever view is selected. The grass is generated anew for
        // wherever the camera is each frame, so what a reach costs is measured while moving as well as
        // standing; with a fixed clock (--fixed-dt) two runs walk the same path.
        else if (m_route == "walk")
        {
            const float yaw = glm::radians(m_startView.yaw);
            const glm::vec2 heading(-std::sin(yaw), -std::cos(yaw));
            GoTo(m_startView.xz + heading * (WALK_SPEED * m_routeTime), m_startView.height,
                   m_startView.yaw, m_startView.pitch);
        }
        else if (m_route == "turn")
        {
            GoTo(m_startView.xz, m_startView.height, m_startView.yaw + TURN_RATE * m_routeTime, m_startView.pitch);
        }
```

A heading of yaw degrees points along (−sin yaw, −cos yaw) on the ground, the camera's forward direction at zero pitch,
as `GoTo` turns it. In `SelectView`, below `m_route.clear();`, add:

```cpp
    m_haveStartView = false;   // Chapter 58 section 9: only a ground view below sets it; the Viewpoint and the plates have none
```

and below the line `GoTo(view.xz, view.height, view.yaw, view.pitch);` inside the loop over the views, add:

```cpp
                m_startView = { view.xz, view.height, view.yaw, view.pitch };   // Chapter 58 section 9
                m_haveStartView = true;
```

In `SelectRoute`, replace the `if` at its top, from `if (name != "edge-sweep" && name != "aerial-orbit"` to its closing
brace, with:

```cpp
    if (name != "edge-sweep" && name != "aerial-orbit" && name != "forest-run"
        && name != "coast-walk" && name != "coast-orbit" && name != "coast-rim"
        && name != "walk" && name != "turn" && !name.empty())
    {
        return InitializationResult::failure(std::format("Unknown Horizon route: {} (edge-sweep, aerial-orbit, forest-run, coast-walk, coast-orbit, coast-rim, walk, turn).", name));
    }
    if ((name == "walk" || name == "turn") && !m_haveStartView)
    {
        // Chapter 58 section 9: these two start from a named view, at its height above the ground.
        return InitializationResult::failure(std::format("The route {} starts from a ground view (Wind edge, Coast and the others of --horizon-view); the Viewpoint and the plates have none.", name));
    }
```

**What the reference measured.** On the reference's RTX 5090 (driver 621.01), at Wind edge, 1920 × 1080, 4x MSAA, a
fixed clock and `--present immediate`, the median GPU frame of 478 frames after 120 to warm up, one run each:

| | standing | walking |
| --- | --- | --- |
| before this chapter: `--grass-canopy 0 --coast-grass-reach 42 --grass-reach-fade 0` | 3.377 ms | 3.270 ms |
| the default: the canopy on, 120 m, a 30 m fade | 4.396 ms | 4.268 ms |
| 120 m and the 30 m fade, the canopy off | 4.157 ms | |

The default costs about 1.0 ms over the frame before the chapter, standing or walking. The frame budget is 16.7 ms at 60 fps; these numbers are the RTX 5090's, a far
faster GPU than the laptop the guide budgets for, which has not been measured. The first and third rows were measured
on the chapter's code before a last change to the march, which does not run with the canopy off.

<a id="ch58-cost"></a>

### Attempt CH58-cost: which term grows fastest

Predict first: going from the 42 m reach to the default, which part of the frame grows most, the cards, their shadow
casters, the generation pass or the canopy? Then measure your own frame, standing and walking, before and at the
default.

**Acceptance:** your four numbers, named with your GPU, and the default's cost over the frame before the chapter.

**Transfer:** the generation pass's own timer reads about 0.005 ms at 42 m and 120 m and jumps to about 0.3 ms at 160 m,
while the whole frame grows smoothly. What does that say about the timer, and what would you measure to find out?

<details>
<summary>Hint 1: what the cards cost</summary>

Section 1's attempt: the clump draw doubled from 42 to 200 m. How many camera clumps does 120 m add, with the band?

</details>

<details>
<summary>Hint 2: the canopy</summary>

The canopy's march costs every terrain pixel the same, whatever the reach. Its cost is the second and third rows'
difference.

</details>

<details>
<summary>Hint 3: the timer</summary>

A timestamp pair brackets an interval of the queue, not a kernel. What else can run on the GPU between two
timestamps?

</details>

<details>
<summary>Worked solution: the cards, then the canopy; the generation pass is a few microseconds</summary>

The cards. On the reference, at Wind edge, the clump draw grew from 0.95 ms at 42 m to 1.63 ms at 120 m with no band
(camera clumps 628 to 2,456), and the band brings the camera clumps at 120 m down to 2,049; their shadow casters grow
with them. The canopy is about 0.24 ms at either reach. The generation pass reads a few microseconds at both.

**Answer to the transfer.** A timer whose interval jumps while the frame grows smoothly is measuring something else
as well. Both of its timestamps stand at the end of all prior commands, so the interval can take in other work that
the queue runs between them; the reference found that above 120 m the reading takes in up to about 0.2 ms that other
timers also count, and gives no cause beyond that. Measure the frame with and without the pass, not the pass's own
timer.

</details>

### Checkpoint

No file is new, and the supplied test stays at stage 6. Build Release, then measure your own frame:

```powershell
$cases = [ordered]@{
    'before-standing'  = @('--grass-canopy', '0', '--coast-grass-reach', '42', '--grass-reach-fade', '0')
    'before-walking'   = @('--grass-canopy', '0', '--coast-grass-reach', '42', '--grass-reach-fade', '0', '--horizon-route', 'walk')
    'default-standing' = @()
    'default-walking'  = @('--horizon-route', 'walk')
}
foreach ($name in $cases.Keys)
{
    $extra = $cases[$name]
    & ./Build/Artifacts/Release/SandboxGame/SandboxGame.exe --demo Horizon --horizon-view "Wind edge" --msaa 4 `
        --width 1920 --height 1080 --present immediate --fixed-dt 0.016666667 --frames 600 --warmup 120 `
        --benchmark "$name.csv" @extra
    $times = @(Import-Csv "$name.csv" | ForEach-Object { [double]$_.gpu_render_ms } | Sort-Object)
    '{0}: median {1:N3} ms' -f $name, $times[[int][math]::Floor($times.Count / 2)]
}
```

Name your GPU beside the four numbers. Run `--horizon-route turn` too: in place, turning 6 degrees a second, the frame
moves through the tiles at the edge of the view, not the reach. `--horizon-route walk` from the Viewpoint stops at the
start with the message `The route walk starts from a ground view (Wind edge, Coast and the others of --horizon-view);
the Viewpoint and the plates have none.`

Next: what the chapter does not do yet, and the exit check.

## 10. What Chapter 58 does not do yet, and the exit check

The coastal grass now runs from the blades at your feet through the cards to the canopy at the horizon, from one
population and one light. This section has no attempt: each item below is a limit, stated here so that you need not
find it.

### What it does not do

- **The near cover at Coast, 30 to 50 m, is short.** Against the fair reference (real blades at full density, rendered
  eight times finer and averaged), on the reference's RTX 5090 at 1920 × 1080, 4x MSAA, frame 90, standing, with the
  canopy drawn for the whole population in a build only the reference has, the canopy holds 60, 75, 60 and 92 % of the
  reference's optical depth at 30-40, 40-50, 50-60 and 60-70 m (the 50-60 m band rests on few pixels: the
  reference's own gap there is 0.006; the tile and its pixels are in `REFERENCE.md`). The ground
  there is nearly level, so the march's length is not the cause; the cause is not shown. Three candidates were named and
  none tested: the 128-pixel capture under-counting thin blades, the habitat at a sample differing from the density the
  generator admits, and the clumps standing on a jittered grid, which hides more ground than a random field.
- **Wind edge's far meadow is darker than real grass.** At 70 to 100 m the canopy reads 11 to 28 % darker than the
  blades of the fair reference in every channel (1920 × 1080, 4x MSAA, frame 90, standing, at the defaults; a tile of
  an 8 × 8 grid, given with its pixels in `REFERENCE.md`; 70 to 80 m, 80 to 90 m and 90 to 100 m), and at 140 to 160 m up to 39 % darker in red and blue but 6 % in green. At 70 to 100 m the three channels move
  alike, which suggests the light more than the cover; that was not tested.
- **The far ground is smooth.** The fair reference's tiles at frame 90, blades to 200 m, show clumps and gaps far off;
  the canopy is an average, so it is even.
- **Forest floor is uneven** against the fair reference, by up to about a fifth either way per channel at 60 to 90 m
  and more in one band; those figures were not checked a second time.
- **A convex break is marched short.** Where the ray grazes a ledge on its way back to the eye (the supplied test's
  case: a 5 m ledge 110 m out), the march takes 0.40 of that ray's depth. Running the march on to the eye reads 1.01
  with 8 samples and 1.14 with 32, which is aliasing, not a cure, so the chapter does not do it.
- **The beach strip turns green.** Where the habitat map grows dune grass along the beach, the canopy paints it green
  out to the horizon; the reference's blades stop at 130 m there.
- **From the Viewpoint the meadows are a greyer, mottled green**, and the dune grass covers part of the beach line:

  ![Two strips of Horizon from the 1 km Viewpoint, one above the other, frame 90. Above, before this chapter: green meadows, brown soil lines and grey ridges, a pale beach line along the sea. Below, with the canopy: the same island, the meadows a greyer, more mottled green, and the pale beach line mostly gone under green.](images/58-viewpoint.png)

  (Rows 420 to 759 of frame 90 on the reference's RTX 5090: above, the build before this chapter; below, the
  defaults.)
- **The reach is provisional.** 120 m with a 30 m fade costs about 1.0 ms over the frame before the chapter on the RTX
  5090. It is to be checked on the RTX 4060 Laptop, which may lower it.
- **The canopy lies on the ground plane and stands still.** It has no height on screen and no parallax, it does not
  move in the wind while the cards over it do, it casts no shadow, and it draws no silhouette against the sky on a
  ridge.
- **Only Horizon has it.** The Grass demo rebakes its capture when its settings change and never reads it back, so it
  has no table and no canopy.
- **The canopy arrives on frame 3**, when the copy of the bake in frame 1 is taken after its slot's fence.

### Exit check

Under [the hygiene every exit check assumes](../VulkanTutorial.md#conventions-every-chapter-uses), build Release and
Debug, then run each and check what it says.

**Before the chapter, byte for byte.** With the three flags, the program draws the frames of the kept build at the five
views whose frames repeat to the byte:

```powershell
foreach ($view in 'Wind edge', 'Coast', 'Forest floor', 'Lone tree', 'Viewpoint')
{
    $name = $view -replace ' ', '-'
    & ..\SandboxGame-before-58\SandboxGame.exe --demo Horizon --horizon-view $view --msaa 4 --width 1920 --height 1080 `
        --fixed-dt 0.016666667 --frames 90 --sequence "$name-before-58" --sequence-first 30 --sequence-last 90 --sequence-every 30
    & .\Build\Artifacts\Release\SandboxGame\SandboxGame.exe --demo Horizon --horizon-view $view --msaa 4 --width 1920 --height 1080 `
        --fixed-dt 0.016666667 --frames 90 --sequence "$name-58" --sequence-first 30 --sequence-last 90 --sequence-every 30 `
        --grass-canopy 0 --coast-grass-reach 42 --grass-reach-fade 0
}
Get-FileHash *-before-58\*.bmp, *-58\*.bmp | Sort-Object Path | Format-Table Hash, Path
```

On the reference's RTX 5090 all fifteen pairs were equal on the chapter's code before a last change to the canopy's
march, which does not run with the canopy off, and Coast's and Wind edge's again after it. Stream and the Grass demo
are left out: neither repeats to the byte on a GPU, even run against itself. The reference measured Stream's frame 30
differing from its own second run in one pixel by one code, cause not shown, and the Grass demo's frames differing
from their own repeat by one to five pixels, the order in which its atomics hand out slots
([Chapter 26, section 9](26-Grass-GPU-Generation.md#9-occlusion-culling-against-last-frames-depth)).

**The look.** At the defaults:

```powershell
& ./Build/Artifacts/Release/SandboxGame/SandboxGame.exe --demo Horizon --horizon-view "Wind edge" --msaa 4
```

- The grass reaches the horizon; past the cards the meadow is grass, not section 1's flat ground.
- Tick **Show canopy cover** and look for a grey with no ring through 90 to 120 m.
- Untick **Grass canopy**: the flat ground is back past the cards. Untick **Island grass**: the blades, the cards and
  the canopy all go. With **Ground materials** off the ground is Chapter 37's, with no canopy.
- In the **Grass view** list, the four light views (**Ambient**, **Diffuse**, **Transmission**, **Specular**) paint the
  canopy's own term too; **Coverage** and the other views show the blades only.

**Validation.** A Debug run of Horizon at Wind edge and at Coast, at the defaults, prints the `VALIDATION-SETTINGS`
notice and two `WARNING-Shader-OutputNotConsumed` (locations 2 and 3), the three lines the build before this chapter
prints; the chapter adds none:

```powershell
& ./Build/Artifacts/Debug/SandboxGame/SandboxGame.exe --demo Horizon --horizon-view "Wind edge" --msaa 4 --frames 60
& ./Build/Artifacts/Debug/SandboxGame/SandboxGame.exe --demo Horizon --horizon-view Coast --msaa 4 --frames 60
```

**Every test.** Every `Tutorial*` test project passes in Debug and Release, `TutorialGrassCanopyTests` at stage 6 and
`GRASS_CANOPY_TEST_CONTROL` at 0, with controls A to D and control 4 put back. This loop builds the whole solution in
each configuration, one compiler at a time as [Premake.md](../Premake.md) explains, and runs every test from the
repository root:

```powershell
foreach ($config in 'Debug', 'Release')
{
    & 'C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe' .\Build\Projects\PillowFort.sln /m:1 /nr:false /p:CL_MPCount=1 /p:UseMultiToolTask=true /p:MultiProcMaxCount=1 /p:EnforceProcessCountAcrossBuilds=true "/p:Configuration=$config" /p:Platform=x64
    if ($LASTEXITCODE -ne 0) { throw "The $config build failed." }
    foreach ($test in Get-ChildItem ".\Build\Artifacts\$config\Tutorial*\Tutorial*.exe")
    {
        & $test.FullName
        if ($LASTEXITCODE -ne 0) { throw "$($test.Name) failed in $config." }
    }
}
```

Two of them print an error on purpose and still exit 0: `TutorialFrameFailureGpuTests` an injected `[ERROR]`, and
`TutorialSyncValidationControl` its planted hazard.

### What the tests catch, and what nothing catches

Each control below was planted in the reference and undone, unless its row says it was not run. A CPU stage catches
most; the rest need the picture or a GPU run.

| Control | Caught by |
| --- | --- |
| A stage 0 number that is not the engine's (the schedule, the clump density, the tiles of a reach) | stage 0 (not run) |
| The cards' share as the ramp `max(D - b / 2, 0)` (control 1) | stage 2 |
| The fold dividing each texel by its alpha before averaging (control 2) | stage 3 |
| A block field written to the wrong member, or the cover view without the canopy | stage 4 (not run) |
| The grass's light as a function, not an included body | section 6's checkpoint: the grass's Release SPIR-V differs; on screen, one or two pixels by one code |
| The row weights summed from the bottom (control 3) | stage 5 |
| A sample under the ground counted (control 4) | stage 5 |
| Level ground's march, H / V.y, on ground falling away from the eye | stage 5: 0.11 to 0.63 of the whole ray's depth, against 1 |
| The barrier before the copy naming the blit stage (A) | sync validation in Debug: three `SYNC-HAZARD-READ-AFTER-WRITE` at `vkCmdCopyImageToBuffer` |
| The last barrier without `COPY` in its source (B) | three `SYNC-HAZARD-WRITE-AFTER-READ` at `vkCmdPipelineBarrier2` |
| `RecordCanopy` without barrier (a) (C) | at `--msaa 1` only: ten `SYNC-HAZARD-WRITE-AFTER-READ` and one `SYNC-HAZARD-WRITE-AFTER-WRITE` at `vkQueueSubmit2`; silent at 4x |
| Barrier (b) naming the vertex stage (D) | ten `SYNC-HAZARD-READ-AFTER-WRITE` at `vkCmdDraw` |
| `reachFadeBand` added as a new member, growing `GrassParameters` | `static_assert`, and `PlantWindTests`' golden block (not run) |
| The canopy's lines outside `PF_GRASS_CANOPY` | section 6's `.spv` comparison, rerun: beside the three grass modules a correct tree differs in (section 7's checkpoint) and its 139 before, 140 after, `Terrain.frag.spv` differs; and the exit check's hashes (not run) |

What nothing catches: the barrier from the copy to the host (sync validation does not look across the fence wait; it
is argued by Chapter 4's three questions); far cards overlapping, which share Chapter 47's sample masks and hide less
than the law says, while the canopy fills only the missing share; the canopy reading each sample's habitat where
the generator takes a clump's least over its footprint, which can leave a faint fringe at a forest's edge or a soil line;
and a colour a few percent off, which only a comparison with the fair reference shows (`REFERENCE.md`'s Chapter 58
section has the reference's numbers).

### Where to go from here

**A macro capture and a coarse hierarchy.** [Chapter 48](48-Grass-In-The-Coastal-Pipeline.md) named a capture of a
whole patch of clumps, and coarser levels above it, for grass seen from very far. The canopy is the coarsest level of
that hierarchy with no capture of its own: a patch capture between the cards and the canopy would give the far field
back its clumps and gaps.

**Height and wind for the canopy.** Lifting the canopy's surface 0.3 to 0.5 m off the ground, with parallax, would let
it stand on a ridge against the sky; a gust's brightness, read from the fronts the cards answer, would move it with
them.

Back on the far-view route: return to [43 — Waves to the Shore](43-Waves-To-The-Shore.md).

