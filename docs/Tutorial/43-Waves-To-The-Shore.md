# 43. Waves to the Shore

> **Reference support:** named prepared-exercise and native-regression commands
> in this lesson run from the [reference checkout](../BranchWorkflow.md#prepared-reference-exercises).
> The growing chapter implementation remains in your learning checkout.

Start with gentle long waves on one fixed coastal patch. Do not begin with
foam. A white edge can hide water being created, a moving bed, or two copies
of the same crest. Bores, calibrated breaking and shorter dispersive waves
are separate later work. Chapter 42's shared tree-wind work is not a prerequisite
for these water problems and is not implemented by this chapter.

**Delivery status:** The gentle-wave milestone and two paired Release
exercises are built and verified on both GPUs. Read [the evidence](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/REFERENCE.md)
for configurations, measured budgets and remaining limitations. This is not
the complete shoreline plan: actual-coast phase/reflection calibration,
shorter dispersive waves and surf remain separate work.

The chapter builds on Chapter 41's coastal area (`CoastalArea`,
`SeaSurface`), Chapter 29's starting waves `h0` (section 7) and Chapter 30's
three cascades, Chapter 35's reversed depth (section 6), Chapter 18's depth
resolve (section 5), Chapter 28's Beer-Lambert law (section 2), and the GGX
and image-based lighting of Chapters 15 and 24.

## Files And Experiments

| File | Responsibility |
| --- | --- |
| [ShorelineDomain.h](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Shaders/Shoreline/ShorelineDomain.h) | Fixed world footprint and bed-cache coordinates |
| [Terrain](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/Demos/Horizon/Terrain.h) | Authoritative coastal bed nodes and cell means |
| [ShorelineReference.h](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/Demos/Horizon/ShorelineReference.h) | Double-precision transport oracle, not a frame-loop solver |
| [ShorelineStep.comp.glsl](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Shaders/Shoreline/ShorelineStep.comp.glsl) | Production hydrostatic reconstruction and conservative GPU transport |
| [ShorelineSimulation](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/Demos/Horizon/ShorelineSimulation.h) | State, ledger, bounded retries, publication and diagnostics |
| [ShorelineClock.h](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/Demos/Horizon/ShorelineClock.h) | Physical ticks, backlog and presentation time |
| [ShorelineIncident.comp.glsl](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Shaders/Shoreline/ShorelineIncident.comp.glsl) | Actual offshore H0 components, finite-depth boundary targets |
| [ShorelineSurface](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/Demos/Horizon/ShorelineSurface.h) | Presentation of published flow, without another water draw |
| [CoastalArea](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/Demos/Horizon/CoastalArea.h) | Owner: initial flood fill, clock, per-frame ticks, controls and statistics |
| [ShorelineSampling.glsl](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Shaders/Shoreline/ShorelineSampling.glsl), [ShorelineFriction.comp.glsl](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Shaders/Shoreline/ShorelineFriction.comp.glsl) | Characteristic boundary and relaxation strip; Manning drag |
| [ShorelineAdaptive.comp.glsl](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Shaders/Shoreline/ShorelineAdaptive.comp.glsl), [ShorelineDiagnostics.comp.glsl](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Shaders/Shoreline/ShorelineDiagnostics.comp.glsl) | GPU-side CFL retry; field reduction and all-or-nothing publication |
| [ShorelineSurface.comp.glsl](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Shaders/Shoreline/ShorelineSurface.comp.glsl), [ShorelineWetMaterial.glsl](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Shaders/Shoreline/ShorelineWetMaterial.glsl) | Wet history, the node atlas, and the ground's wet-material handoff |
| [ShorelineOptics](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/Demos/Horizon/ShorelineOptics.h), [SeaTransmission.glsl](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Shaders/Sea/SeaTransmission.glsl) | Opaque color/depth snapshots; contact tolerance and refraction tests |
| [VulkanInstance.cpp](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/VulkanGraphics/VulkanInstance.cpp) | Enables `VK_EXT_conditional_rendering` when the device offers it |
| [CPU tests](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/ShorelineTests.cpp), [GPU tests](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/ShorelineGpuTests.cpp) | Fields and deliberately broken controls, not just screenshots |
| [Chapter43Numerics.h](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/Checkpoints/Chapter43Numerics.h) | Editable CPU face, Euler, CFL and RK2 calculation |
| [Chapter43Numerics.cpp](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/Checkpoints/Chapter43Numerics.cpp) | Protected arithmetic checks, broken-pressure control and unchanged reference comparison |

In the current reference, `ShorelineSimulation`, `SurfaceFields` and
`OpaqueInputs` delete copying and supply no move operation. `CoastalArea`
keeps these GPU owners at stable addresses and rebuilds their resources
through initialization and shutdown. This is the written GPU continuation's
contract; the sealed CPU numerics export keeps its pinned headers unchanged.
CPU oracle grids and diagnostic records remain values.

Write down the units before editing: bed `b` and free surface `eta` are metres
above the same datum; depth `h = max(0, eta-b)` is metres; `q = h*(u,v)` is
depth-integrated transport in square metres per second. A cell stores
`(h,qx,qz)`. Horizontal choppy FFT displacement is not `q`.

No earlier chapter teaches numerical fluid flow. Begin with the two-cell CPU
calculation in section 0 before assembling the full solver in sections 2 and 3.
A finite-volume cell stores the *average* of `(h,qx,qz)` over its square, not
a point sample. Neighbours exchange the same face flux with opposite signs.
An explicit step also limits how far information can travel in one update.
The calculation below makes those three statements observable.

Names the worked answers use: *HLL* (Harten, Lax and van Leer) is an
approximate Riemann solver; from the states on the two sides of a face and
estimates of the fastest left- and right-going wave speeds, it returns one
flux through that face. *MUSCL* reconstruction gives each cell a limited
linear slope instead of a constant. It improves accuracy in smooth monotone
regions, while reducing slopes near sharp changes and extrema to control
overshoots. *RK2* is the two-stage strong-stability-preserving
Runge-Kutta step (Heun's method) written out in section 2. The *CFL*
(Courant-Friedrichs-Lewy) number, `dt*speed/dx`, is how many cells a wave
crosses in one step; an explicit solver is stable only below a scheme-specific
limit, and section 3 gives this one's. The *ledger* records, per cell, the
volume that crossed an open boundary, that the boundary's relaxation strip
added or removed, and that clamping a negative depth added back, so every
change in total volume is explained. *Publishing* a state copies a checked
solver state into the buffer that rendering reads (section 4). Toro's
*Riemann Solvers and Numerical Methods for Fluid Dynamics* covers HLL and
MUSCL in depth.

To watch the solver, select `Coast shore` (eye level at the waterline) or
`Coast water aerial` in Horizon's Viewpoint list. The Coastal area controls
hold Paused, Step, Reset water and the Coastal view selector (Water,
Elevation, Depth, Speed, Wetness). The Coastal systems statistics panel shows
the water clock, its backlog, the last tick's subdivisions out of 8, and the
ledger: volume, boundary and source volume, dry correction and the
unaccounted residual. Several acceptance criteria below can be watched there
before any test runs.

## Runnable Problems

Start with the CPU-only `ch43-numerics` source checkpoint in section 0. It
exports the small driver and the actual double-reference header together;
it requires neither a Vulkan device nor the assembled Horizon renderer.
It is a solution checkpoint for inspecting and changing the calculation,
not a historical Chapter 43 snapshot or a paired incomplete starter.

Two paired exercises each start from the same pinned, complete source with
one piece removed, so it still builds: `ch43-clock` for Problem 3 and
`ch43-wet-history` for Problem 5. They are exercises on the assembled
project, not reconstructions of an earlier state of the code. Run them from
the repository root (the outer checkout, not a prepared stage tree), in
PowerShell 7:

```powershell
.\Tests\TutorialHarness\Stages\Invoke-LearningStage.ps1 -Stage ch43-clock -Variant Starter -Configuration Release -ExpectIncomplete -ReuseNativeDependencies -BuildWorkers 1 -MinimumAvailableMemoryMiB 4100 -MemoryFloorMiB 3072
.\Tests\TutorialHarness\Stages\Invoke-LearningStage.ps1 -Stage ch43-clock -Variant Solution -Configuration Release -ReuseNativeDependencies -BuildWorkers 1 -MinimumAvailableMemoryMiB 4100 -MemoryFloorMiB 3072
```

Substitute `ch43-wet-history` for the other pair. The memory flags make the
runner refuse to start with less than 4100 MiB of free RAM and stop a run
that falls below 3072 MiB; `-BuildWorkers 1` keeps one compiler process.
Without the memory flags the runner skips both checks, so a machine with
ample memory can leave them out. The starter must build and run, fail only
its named acceptance check, and leave unrelated invariants healthy. Its smoke
run is 4201 frames at a fixed 1/60 s, 70 s of physical time at the
`Coast shore` viewpoint, and then exits; it is not an interactive session.
The clock starter can look normal at 60 Hz; predict its 30 Hz result before
running acceptance. That is the problem, not a missing include or a crash.

Edit the starter under `Build/LearningStages/ch43-clock/Starter/Source/`;
the ready solution is in the separate `Solution/Source` tree beside it.
Read the problem first; open hints only as needed. For an already prepared
tree use `-Action Verify` rather than preparing it again. After fixing a
starter, omit `-ExpectIncomplete`: acceptance must now pass, not merely
reproduce its old defect. Add `-Gpu Radeon -EvidenceName Radeon`
to verify the same tree on the second device. See the [runner guide](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/Stages/README.md)
for paths, repairs and evidence retention. Stage verification status is tracked
in [REFERENCE.md](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/REFERENCE.md).

## 0. A Face, A Still Lake, And A Stable Step

### The Calculation Recipe

Use the cell averages and units defined above. For this first calculation,
take a one-dimensional strip: `U=(h,q)` and wet velocity `u=q/h`; use zero
velocity when dry. A **flux** is a transfer rate through a face. The physical
shallow-water flux is `F(U)=(q, q*q/h + g*h*h/2)` for a wet column, and zero
when dry. The second component includes water pressure, so still water can
have nonzero momentum flux without moving.

At a bed step, reconstruct both sides against the higher bed:

```text
bStar = max(bLeft, bRight)
hLeftStar  = max(0, hLeft  + bLeft  - bStar)
hRightStar = max(0, hRight + bRight - bStar)
ULStar = (hLeftStar,  hLeftStar  * uLeft)
URStar = (hRightStar, hRightStar * uRight)
```

Keep each original velocity when forming its star transport. A shallow-water
disturbance travels at `u ± sqrt(g*h)`. HLL bounds the reconstructed face by
left- and right-going speeds, including zero:

```text
a = min(0, uLeft-sqrt(g*hLeftStar), uRight-sqrt(g*hRightStar))
b = max(0, uLeft+sqrt(g*hLeftStar), uRight+sqrt(g*hRightStar))
Fface = (b*F(ULStar) - a*F(URStar) + a*b*(URStar-ULStar)) / (b-a)
```

Apply that expression component by component. For two dry sides return zero
instead of dividing by `b-a=0`. The shared mass flux has one left-to-right
orientation. Momentum also needs a correction for each side's removed column:
`PLeft=g*(hLeft*hLeft-hLeftStar*hLeftStar)/2`, with the analogous `PRight`.
Add the cell's own correction to its momentum flux at that face.

A cell then takes one explicit Euler step:
`Unew=Uold-(dt/dx)*(Feast-Fwest)`. The shared mass rate leaves the left cell
and enters the right cell through that subtraction; do not negate it a second
time. For a reflecting end wall, use a ghost column with the same bed/depth
and reversed `q`. A ghost column supplies a boundary face state; it is not an
extra volume of water stored in the domain.

**A different small example:** two identical columns with `h=2 m`, `q=0` on
a flat bed give `Fface=(0,19.62)` at `g=9.81`. A cell with that same pressure
on both faces has zero flux difference, so its depth and transport stay
unchanged. Zero transport does not mean zero pressure.

For square cells, this implementation's two-dimensional stability estimate is
`dtMax=0.2*dx/(abs(u)+abs(v)+2*sqrt(g*h))`; take the smallest bound over wet
cells. The factor `0.2` belongs to this second-order scheme, not every HLL
solver. A full RK2 step evaluates two Euler stages, then averages the original
state with the second stage's result; the first paper exercise asks for one
Euler stage only. Now apply the recipe to unequal
columns and a bed step, keeping the numerical answers closed until needed.

<a id="ch43-numerical-bridge"></a>

### Attempt CH43-numerical-bridge: move water without inventing it

Work on paper before running the CPU checkpoint. Use two adjacent 1 m cells
in a strip one metre wide, `g=9.81 m/s^2`, and reflecting end walls. Positive
`q` and positive face mass flux point to the right. Both cells use the same
left-to-right orientation for their shared face; do not flip that face flux
when visiting the right cell.

1. On a flat bed, release a left column `h=1 m, q=0` into a dry right column.
   Calculate the shared HLL flux and one Euler update with `dt=0.05 s`.
   Explain why the dry cell can gain water even though both initial velocities
   are zero.
2. Raise the right bed to `0.5 m` and set depths to `1 m` and `0.5 m`, both
   with zero transport. The free surface is now level at `eta=1 m`.
   Calculate the hydrostatic face and each side's pressure correction.
   Show why this update stays still and what fails if corrections are removed.
3. For a 1 m square cell with `h=1 m`, `u=3 m/s`, `v=4 m/s`, calculate this
   implementation's second-order CFL limit. Does a `1/60 s` physical tick
   fit? Does dividing that tick in two initially fit?

**Acceptance:** Predict the printed face fluxes, depths and CFL limit before
running. Both depth updates conserve the closed strip's volume; the lake
preserves zero transport. The omitted-pressure control creates measurable
artificial transport. A moving wet/dry strip must also remain finite and
nonnegative while matching the unchanged `ReferenceGrid` fields under RK2.
Zero, negative, nonfinite and excessive timesteps are rejected before mutation.

**Transfer:** Change the bed step to `0.25 m`, preserving `eta=1 m`, and
predict both pressure corrections. Then change the moving cell's depth to
`4 m`: calculate the new CFL bound before changing its timestep.

<details>
<summary>Hint 1: flux is a rate, not a depth</summary>

For a 1D column `U=(h,q)`, the physical flux is
`F(U)=(q, q*q/h + g*h*h/2)` when wet. Its components have different units:
`Fh` is `m^2/s`, while `Fq` is `m^3/s^2`. Multiplying the flux difference by
`dt/dx` converts them to the units of `h` and `q`. Interior mass flux appears
once with a minus sign and once with a plus sign in the total volume.

</details>
<details>
<summary>Hint 2: the shared face has two pressure balances</summary>

Reconstruct both columns against `bStar=max(bLeft,bRight)`. Retain each
column's original velocity, but use its reconstructed nonnegative depth for
the HLL states. The mass flux is shared; momentum also receives the bed's
side-specific hydrostatic pressure correction. At a wall, reverse transport
in the ghost column and retain its depth and bed.

</details>
<details>
<summary>Hint 3: the production bound includes both horizontal directions</summary>

Shallow-water signals travel at `u-sqrt(g*h)` and `u+sqrt(g*h)` in x, with the
analogous speeds in z. Here the production scheme bounds their directional
contributions by `abs(u)+abs(v)+2*sqrt(g*h)`. Use the chapter's second-order
CFL number `0.2`; do not replace that sum by the velocity magnitude or a
one-dimensional bound just because this first example is drawn as a strip.

</details>
<details>
<summary>Worked solution: one shared flux, balanced pressure, bounded time</summary>

The shallow-water equations and characteristic speeds are developed in the
[Clawpack authors' approximate Riemann-solver chapter](https://www.clawpack.org/riemann_book/html/Shallow_water_approximate.html).
Their HLL discussion motivates replacing the unresolved face solution by two
bounding waves. Here we use the same speed estimates as PillowFort's
`riemann`, clipped to include zero. The bed treatment is the hydrostatic
reconstruction of [Audusse et al. (2004)](https://perso.math.u-pem.fr/bouchut.francois/publications/hydroproj_published.pdf).
The numbers below are calculations for our local fixture, not measured wave
calibration or a derivation of a general stability theorem.

Let `u=q/h` for wet columns and zero for dry columns. After hydrostatic
reconstruction, call the conserved states `ULStar` and `URStar`; the star
transport is the star depth times the *original* side velocity. Define

```text
a = min(0, uL-sqrt(g*hLStar), uR-sqrt(g*hRStar))
b = max(0, uL+sqrt(g*hLStar), uR+sqrt(g*hRStar))
F = (b*F(ULStar) - a*F(URStar) + a*b*(URStar-ULStar)) / (b-a)
```

Two dry columns have `a=b=0`; return zero flux instead of dividing by zero.
For the flat wet/dry face, `a=-sqrt(9.81)`, `b=sqrt(9.81)`,
`F(ULStar)=(0,4.905)` and `F(URStar)=(0,0)`. Substitution gives
`Fh=sqrt(9.81)/2=1.566045977 m^2/s` and
`Fq=9.81/4=2.4525 m^3/s^2`.
The mass transfer comes from the pressure-driven Riemann problem, not an
arithmetic average of the two initial transports.

For each cell the update is `Unew=Uold-dt/dx*(Feast-Fwest)`, with the
appropriate side pressure correction added to each momentum flux. Reflecting
walls have zero mass flux; their momentum fluxes initially equal `4.905`
at the wet left wall and zero at the dry right wall. Thus the *Euler* result
at `dt=0.05 s` is

| Cell | Depth `h` (m) | Transport `q` (`m^2/s`) |
| --- | --- | --- |
| Left | `0.9216977012` | `0.122625` |
| Right | `0.0783022988` | `0.122625` |

The water volume stays `1 m^3`. The sum of transport need not stay zero:
the end walls exert pressure forces. A full RK2 step has a different final
state because it evaluates a second Euler stage; do not compare this table
directly with `ReferenceGrid::Step`'s final output.

For the still lake, `bStar=0.5 m` and both reconstructed depths equal
`0.5 m`. Their velocities are zero, giving `Fh=0` and
`Fq=g*0.5^2/2=1.22625`. The side corrections are

```text
PL = g*(1^2-0.5^2)/2   = 3.67875
PR = g*(0.5^2-0.5^2)/2 = 0
```

The left cell sees shared-face momentum flux `Fq+PL=4.905`, exactly its
left wall's pressure. The right sees `Fq+PR=1.22625`, exactly its right
wall's pressure. Both momentum differences vanish. Remove `PL`, and the
left column spuriously gains `0.05*(4.905-1.22625)=0.1839375 m^2/s`.
Zero mass error alone would miss that failure.

Put the two C++ listings below, in order, in the editable
[Chapter43Numerics.h](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/Checkpoints/Chapter43Numerics.h).
The first opens `tutorial::shoreline_numerics`; the second closes it after
the time-update functions. Keep the functions `inline` because they are
defined in a header. The protected [checkpoint driver](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/Checkpoints/Chapter43Numerics.cpp)
supplies the test fixtures, independent expected values, unchanged-oracle
comparison and `main`; leave that driver unchanged when experimenting.
`GRAVITY` and `DRY_DEPTH` come from `ShorelineReference.h`; that header is
copied into the export as an input and is not rewritten to make the exercise
pass. These are the complete face and first-order spatial update mechanisms:

```cpp
#pragma once
#include "PillowFort/Demos/Horizon/ShorelineReference.h"
#include <algorithm>
#include <cmath>
#include <stdexcept>
#include <vector>

namespace tutorial::shoreline_numerics
{
using pf::demos::horizon::shoreline::DRY_DEPTH;
using pf::demos::horizon::shoreline::GRAVITY;

struct Column
{
    double h = 0;
    double q = 0;
};

struct Face
{
    Column flux;
    double leftPressure = 0;
    double rightPressure = 0;
};

inline Face HydrostaticFace(Column left, Column right, double bedLeft, double bedRight)
{
    const double bed = std::max(bedLeft, bedRight);
    const double hl = std::max(0.0, left.h + bedLeft - bed);
    const double hr = std::max(0.0, right.h + bedRight - bed);
    const double ul = left.h > DRY_DEPTH ? left.q / left.h : 0;
    const double ur = right.h > DRY_DEPTH ? right.q / right.h : 0;
    const double a = std::min({0.0, ul - std::sqrt(GRAVITY * hl), ur - std::sqrt(GRAVITY * hr)});
    const double b = std::max({0.0, ul + std::sqrt(GRAVITY * hl), ur + std::sqrt(GRAVITY * hr)});
    const Column fl{hl * ul, hl * ul * ul + 0.5 * GRAVITY * hl * hl};
    const Column fr{hr * ur, hr * ur * ur + 0.5 * GRAVITY * hr * hr};
    Column flux{};
    if (b > a)
    {
        flux = {(b * fl.h - a * fr.h + a * b * (hr - hl)) / (b - a),
                (b * fl.q - a * fr.q + a * b * (hr * ur - hl * ul)) / (b - a)};
    }
    return {flux, 0.5 * GRAVITY * (left.h * left.h - hl * hl),
            0.5 * GRAVITY * (right.h * right.h - hr * hr)};
}

inline std::vector<Column> Euler(const std::vector<Column>& input, const std::vector<double>& bed,
                          double dx, double dt, bool pressureCorrections = true)
{
    std::vector<Face> faces(input.size() + 1);
    faces.front() = HydrostaticFace({input.front().h, -input.front().q}, input.front(), bed.front(), bed.front());
    faces.back() = HydrostaticFace(input.back(), {input.back().h, -input.back().q}, bed.back(), bed.back());
    for (size_t i = 1; i < input.size(); ++i)
    {
        faces[i] = HydrostaticFace(input[i - 1], input[i], bed[i - 1], bed[i]);
    }
    std::vector<Column> output(input.size());
    for (size_t i = 0; i < input.size(); ++i)
    {
        const Face& west = faces[i];
        const Face& east = faces[i + 1];
        const double correction = pressureCorrections ? east.leftPressure - west.rightPressure : 0;
        Column value{input[i].h - dt / dx * (east.flux.h - west.flux.h),
                     input[i].q - dt / dx * (east.flux.q - west.flux.q + correction)};
        if (!std::isfinite(value.h) || !std::isfinite(value.q) || value.h < -1e-12)
        {
            throw std::runtime_error("Invalid arithmetic update; no clamp conceals a flux failure.");
        }
        value.h = std::max(0.0, value.h);
        if (value.h <= DRY_DEPTH) { value.q = 0; }
        output[i] = value;
    }
    return output;
}
```

The fixture's tiny negative round-off cleanup has no cumulative dry-volume
ledger. It checks the chosen closed-strip fixtures' volume to `1e-12 m^3`;
the full solver separately records every dry correction. This is a teaching
calculation of the first-order spatial scheme, not another production water
system. The `pressureCorrections=false` argument is used only by the named
broken control.

Now bound the time update. For the moving square cell, the production
second-order signal estimate is
`3+4+2*sqrt(9.81)=13.26418391 m/s`. Thus
`dtMax=0.2*1/13.26418391=0.01507819866 s` (approximately).
`1/60 s` exceeds it, while `1/120 s` initially fits. The bound must be checked
again on intermediate states; this arithmetic does not guarantee two
substeps suffice throughout a changing flow. Section 3 teaches the complete
transactional retry when they do not. `0.2` is this implementation's limit,
not a universal CFL constant.

The checkpoint's didactic RK2 driver retains the *two-dimensional*,
first-order-spatial reference bound `0.4*dx/max(abs(u)+2*sqrt(g*h))`, with
`v=0`, so a comparison with the real 2D oracle uses the same timestep
contract. It implements the time update as follows:

```cpp
inline double StableStep(const std::vector<Column>& state, double dx)
{
    double signal = 0;
    for (const auto& value : state)
    {
        const double velocity = value.h > DRY_DEPTH ? std::abs(value.q) / value.h : 0;
        signal = std::max(signal, velocity + 2 * std::sqrt(GRAVITY * value.h));
    }
    return signal > 0 ? 0.4 * dx / signal : 1;
}

inline void Step(std::vector<Column>& state, const std::vector<double>& bed, double dx, double dt)
{
    if (!std::isfinite(dt) || dt <= 0 || dt > StableStep(state, dx) * (1 + 1e-12))
    {
        throw std::invalid_argument("Shoreline step exceeds its two-dimensional CFL bound.");
    }
    const auto first = Euler(state, bed, dx, dt);
    const auto second = Euler(first, bed, dx, dt);
    for (size_t i = 0; i < state.size(); ++i)
    {
        state[i] = {(state[i].h + second[i].h) * 0.5, (state[i].q + second[i].q) * 0.5};
    }
}
} // namespace tutorial::shoreline_numerics
```

The fixture compares that result with `ReferenceGrid::Step` on a 12 by 2
grid, repeating the strip in z with `qz=0`. Both z-face pressure contributions
then cancel, but the 2D timestep bound still applies. It also tests a partly
dry stepped lake, an equal moving state and two dry states, rather than only
asserting the printed constants. `TutorialShorelineTests` remains the broader
unchanged oracle suite for two-dimensional lake balance, advancing/retreating
fronts, analytic waves and volume ledgers.

Run the source checkpoint from the repository root in PowerShell 7:

```powershell
$runner = '.\Tests\TutorialHarness\Checkpoints\Invoke-SourceCheckpoint.ps1'
& $runner -Action Prepare -Checkpoint ch43-numerics
& $runner -Action Generate -Checkpoint ch43-numerics
& $runner -Action Build -Checkpoint ch43-numerics
& $runner -Action Check -Checkpoint ch43-numerics
```

This ID requires the C++ compiler and Premake, but no Vulkan SDK headers or
GPU. The runner copies Premake into its self-contained source export. Its
Build and Check phases retain the 4100 MiB launch gate, 3072 MiB runtime floor
and one-worker/serial execution limits described in
[the CPU checkpoint guide](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/Checkpoints/README.md).
The default variant is `Solution`; no paired incomplete starter is claimed.
After Prepare, edit only
`Build/SourceCheckpoints/ch43-numerics/Solution/Tests/TutorialHarness/Checkpoints/Chapter43Numerics.h`
and rerun Build then Check. Do not edit either the protected driver or
`ShorelineReference.h` to change the expected answer. Preparing again refuses
to overwrite that tree; use a new `-Destination` for a fresh copy.

After the arithmetic checkpoint passes, section 1 fixes the actual bed;
section 2 adds MUSCL reconstruction, its within-cell bed source and GPU fields.
The per-face pressure correction alone does not teach that entire second-order
balance, and the simple release fixture does not expand the delivery scope to
authored bores or breaking surf.

</details>

## 1. A Bed That Does Not Move With The Camera

<a id="ch43-fixed-bed"></a>

### Attempt CH43-fixed-bed: make one physical coastline

Use a fixed 256 by 256 cell patch at 1 m spacing. Fly across terrain ring
boundaries and change its visual preset without moving the water's bed.
Decide whether the finite-volume solver stores vertex heights or cell means.

**Acceptance:** Bed fingerprint, initial water volume and a stationary gauge
do not change with camera/ring/preset changes. The rendered nearshore bed
triangles and plant attachment use the same cached nodes. A disconnected low
spot behind a dry ridge must not initialize as ocean.

**Transfer:** Reverse a cell's diagonal. Derive its new area-mean bed before
running the test; a four-corner arithmetic mean is not generally the answer.

<details>
<summary>Hint 1: separate physics from visual LOD</summary>

Camera-dependent terrain sampling is useful for placing a plant on a rendered
ring, but it is not a stationary bathymetry definition.

</details>
<details>
<summary>Hint 2: integrate the actual triangles</summary>

A linear triangle's area mean is the average of its three vertex heights.
The two equally sized triangles need equal weights. The shared diagonal's
endpoints therefore count twice.

</details>
<details>
<summary>Hint 3: initialization also needs connectivity</summary>

Start a flood fill from wet boundary cells, traversing only bed below the
initial sea level. Setting every negative-height cell wet fills isolated pits.

</details>
<details>
<summary>Worked solution: one node cache, several consumers</summary>

`Terrain` constructs a world-fixed cache including the visual rim and a
one-node sampling halo. With corner heights `a,b,c,d` and diagonal `b-c`, the
two triangle means are `(a+b+c)/3` and `(b+c+d)/3`. Thus the solver's cell mean
is `(a+2*b+2*c+d)/6`. `CoastalBed.vert.glsl` renders those same triangles;
triangle interpolation, rather than bilinear interpolation, attaches roots.
The water lattice uses those same 1 m nodes and b-c triangles. Interpolate
nodal `eta-bed` as a varying: subtracting separately interpolated world heights
at the pixel can invent a thin positive film on exactly coincident dry meshes.
The bounded local view draws each 250 m sea tile as a 250-cell lattice, one
cell per 1 m bed node; the legacy standalone sea grid is unchanged. The
visual rim also meets the outside ring's interpolated shading normals, not
just its vertex positions.

Grid alignment alone is insufficient: a camera-centred finite grid can leave
part of the fixed atlas in its stretched horizon skirt. The near water window
therefore covers the union of the atlas and nearby camera, retaining a whole
cell before every skirt vertex. It slides on the same world lattice, without
moving or resetting the solver. When that bounded union no longer fits, water
uses the explicitly approximate far FFT representation; it does not pretend
the missing fine geometry is still an exact local surface.

`ReferenceGrid::FillConnectedOcean` first clears all cells. It seeds only
boundary cells with `b < level`, then visits four-connected neighbours that
satisfy that same condition, storing `h = level-b`. The result is uploaded
once as the initial GPU state. Camera movement does not call this function.

The coarse visual rim is an explicit terrain-LOD approximation outside the
physical patch. It is not evidence that the entire island mesh agrees with
the physical bed to machine precision. Keep its raster seam checks separate
from the exact cached-node tests.

</details>

## 2. Water That Can Both Stay Still And Move

Section 0 treated every cell as a constant column. The next spatial step
keeps the cell average but estimates different states at its two faces.
**MUSCL reconstruction** makes that estimate with a limited slope. For three
free-surface averages `(0,1,2)`, this shader's `limited` function returns a
one-cell increment of `1`, so the middle cell's reconstructed free surfaces
are `0.5` and `1.5`. For `(0,1,1)`, the right difference is zero and the
limited increment is zero: extending the left slope would invent an overshoot.
This is a spatial reconstruction before the face solve, not another time step.

At a local crest `(0,1,0)`, the same limiter also returns zero, so both face
values become `1`. This deliberately falls back to a constant reconstruction
there, even for a smooth crest. Second-order accuracy describes the smooth
monotone part of this method; limiting can reduce its local order and flatten
extrema. [Sekora and Colella](https://arxiv.org/abs/0903.4200v2) (sections 1.4 and 2)
explain that tradeoff and a different, extremum-preserving limiter. This shader
keeps its simpler generalized minmod limiter. A lower crest alone cannot tell
you whether water was lost: inspect the spread of the pulse and its volume
ledger together.

Reconstruct free surface, bed and velocity together; the resulting depth
must remain nonnegative. The within-cell bed source must balance those new
face states as well as the face pressure corrections from section 0. First
recover the constant-column calculation with reconstruction disabled, then
enable the slope and repeat the still-lake check before testing moving water.
The complete second-order balance is supplied in the linked shader; this
small slope example does not derive that whole scheme.

<a id="ch43-balanced-transport"></a>

### Attempt CH43-balanced-transport: preserve a lake without freezing a wave

First preserve a level lake over uneven, partly dry bed. Then advance a dry
front and let a pulse climb and retreat down a slope. Do not add a height clamp
that returns every cell to sea level after the update.

**Acceptance:** Lake depth and momentum stay at rest to round-off (the double
reference allows 1e-11 after 2 s); depth stays finite/nonnegative; a front
wets initially dry cells and later dries them. Closed-basin water volume is
conserved. Open boundaries separately account for flux, forcing and tiny
dry-depth corrections. Compare every GPU
field component against the independent double reference.

**Transfer:** Use another slope and a two-dimensional perturbation. A method
that balances only a flat bed or a one-dimensional strip has not passed.

<details>
<summary>Hint 1: balance flux and gravity together</summary>

At rest, `h` varies while `eta=h+b` is constant. Reconstructing depth alone
without the matching bed source can turn topography into artificial waves.

</details>
<details>
<summary>Hint 2: let both sides see the higher interface bed</summary>

Hydrostatic reconstruction uses `bStar=max(bLeft,bRight)` and nonnegative
interface depths. Each side needs its own pressure correction afterward.

</details>
<details>
<summary>Hint 3: measure what was lost, not only what survived</summary>

Record the boundary mass flux with the same Runge-Kutta weights used by the
state update. Keep source-volume and dry-depth corrections separate. A quiet
height picture does not prove conservation.

</details>
<details>
<summary>Worked solution: hydrostatic HLL, limited reconstruction and RK2</summary>

The implementation follows the hydrostatic reconstruction of
[Audusse et al.](https://perso.math.u-pem.fr/bouchut.francois/publications/hydroproj_published.pdf).
At each face, reconstruct free surface, bed and velocity with the generalized
minmod limiter (`limited`, theta = 1.5, called from `reconstruct`). Limit
depth variation so both face depths remain nonnegative. Given reconstructed
depths `hL,hR`, replace them by

```text
hLStar = max(0, hL + bL - max(bL,bR))
hRStar = max(0, hR + bR - max(bL,bR))
```

Retain the corresponding side velocities and evaluate the HLL flux between
these states. Add the left/right pressure corrections
`g*(hL*hL-hLStar*hLStar)/2` and `g*(hR*hR-hRStar*hRStar)/2` to their respective
momentum balances. MUSCL also needs the within-cell reconstructed bed source
in `ShorelineStep.comp.glsl`; omitting it breaks rest even if the face formula
is correct. The complete `riemann`, `reconstruct` and update functions are in
that file, with an independently evaluated double version in the reference.

Advance with `U1=Euler(U0,dt)` and `U2=(U0+Euler(U1,dt))/2`. Record mass fluxes
and sources at the same half weights. At `h<=1e-4 m`, zero dry-cell momentum;
do not increase that threshold to conceal an unstable advancing front. The
state's fourth component, `w`, is a sticky bit field of numerical failures
(1 CFL, 2 nonfinite, 4 negative depth; higher bits mark solve and relaxation
faults), not foam. Reject failed numerical output instead of shading it as
acceptable water.

Run-up also needs an explicit physical drag choice. The first candidate uses
an authored Manning `n=0.025 s/m^(1/3)`, not a measured island material. For
fixed depth, the [Manning momentum source](https://www.clawpack.org/list/manning.html)
has the exact local update
`qNew=q/(1+dt*g*n*n*length(q)/pow(h,7.0/3.0))`. Apply half of this subflow
before RK2 transport and half afterward (Strang splitting, which keeps the
pair second-order accurate). It preserves depth and momentum direction and
cannot increase kinetic energy. `n=0` recovers the friction-free
control. Check analytic uniform decay, full CPU/GPU fields and sensitivity to
roughness before calling run-up believable; a stable picture is not calibration.

</details>

## 3. The Same Water At Different Frame Rates

<a id="ch43-physical-clock"></a>

### Attempt CH43-physical-clock: retain time under load

Render ten seconds at 30, 60 and 144 Hz. The solver uses a fixed 1/60 s
physical tick, possibly split into smaller stable substeps. Implement pause,
single-step and reset. Give one frame a one-second stall without discarding
the unprocessed time or trying to execute unlimited work.

**Acceptance:** All three schedules execute 600 physical ticks. A stalled
frame consumes at most eight ticks and retains the rest as visible backlog.
Pause holds physics and its presentation; one step visibly advances exactly
one tick, including immediately after reset. Resuming never reverses time.

**Transfer:** Feed zero elapsed time while clearing the backlog. Explain why
zero render elapsed time can still require physical work.

<details>
<summary>Hint 1: two independent limits</summary>

Render-frame work budget limits how many physical ticks run. CFL limits how
small each physical tick must be subdivided. Neither changes physical time.

</details>
<details>
<summary>Hint 2: subtract only work actually done</summary>

Accumulate elapsed time, take the bounded integer number of available ticks,
then subtract exactly that count times the tick duration.

</details>
<details>
<summary>Hint 3: presentation is another clock contract</summary>

Interpolate between the previous and current published states at a common
display time. The FFT must use that same display time. Paused single steps
cannot wait for another running frame before becoming visible.

</details>
<details>
<summary>Worked solution: bounded clock and transactional CFL retry</summary>

The complete, small owner is [ShorelineClock.h](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/Demos/Horizon/ShorelineClock.h).
In its running branch the essential accounting is:

```cpp
m_backlog += elapsed;
count = uint32_t(std::min(double(maximum),
    std::floor((m_backlog + 1e-10) / TICK)));
m_backlog = std::max(0.0, m_backlog - count * TICK);
m_ticks += count;
```

Paused frames consume only a requested single step. The owner retains a
monotonic display time, holds it on pause, advances it by exactly one tick for
a manual step, and resets it with physical time. `CoastalArea::Prepare` uses
the common display time for FFT animation and published-state interpolation.
While running, display time is `Time() - TICK + min(backlog, TICK)`: it trails
physical time by up to one tick, so there are always two published states to
blend. That delay of one tick, about 17 ms, is the price of interpolating
instead of extrapolating.

Follow the host clock too: `FrameInput.deltaSeconds` is capped at 0.1 s so the
camera does not leap after a stall, but `elapsedSeconds` is the unclamped
monotonic time (or the explicit fixed-time test schedule). Horizon passes it
on as `FrameData.time`, and `CoastalArea::Prepare` takes the difference
between successive values. Feeding the capped camera delta into the physical
clock would lose time before the backlog could account for it.

Inside one tick, try 1, 2, 4 then 8 uniform substeps. The step shader flags a
CFL failure when `dt*(abs(u)+abs(v)+2*sqrt(g*h))/dx` exceeds 0.2 in any cell
for the second-order scheme (0.4 for first order), measured on that stage's
input state. Save the complete starting state and cumulative ledger. A CFL
failure restores both before retrying; the dispersive experiment additionally
restores its acceleration guess.
Nonfinite/source/solve faults are not CFL retries. A globally failed tick does
not replace the last valid published surface. A retry is not permission to
clear an unrelated error flag.

The retry decision never travels back to the CPU. Each tick executes
commands for all fifteen possible substeps (1 + 2 + 4 + 8), and
`ShorelineAdaptive.comp.glsl` enables a retry's dispatches only when the
previous attempt failed with a retryable CFL flag. Where the device enables
`VK_EXT_conditional_rendering` (`VulkanInstance` turns it on when present),
that flag predicates the dispatches directly; otherwise the shader writes
zero group counts into indirect dispatch arguments, which still costs one
empty dispatch per skipped step. Re-recording fifteen substeps every tick was
expensive on the CPU, so `CacheAdaptiveCommands` records them once into two
simultaneous-use secondary command buffers, one per ping-pong parity of the
state buffers. Each tick uploads the exact absolute float time for every
possible RK stage. Using a rounded float base plus offsets instead would
subtly change the offshore forcing.
The tick length, iteration count and retry budget are then immutable until a
synchronized reinitialization, so no pending command buffer can reference
replaced commands.

</details>

## 4. One Crest, Not Two

<a id="ch43-offshore-contract"></a>

### Attempt CH43-offshore-contract: drive a bounded coast from the actual sea

Inject one known offshore H0 component before using the random spectrum.
Preserve its frequency, tangential phase and world coordinates. Decide which
wavelengths the physical model can represent, and which surface details are
only a shading approximation. Do not seed another unrelated coastal wave.

**Acceptance:** Measure incoming amplitude/phase and reflected amplitude at
declared gauges. Retain outgoing disturbances rather than overwriting them.
Account for injected/removed water volume. The final geometry contains the
solved long-wave elevation once, not that elevation plus the same FFT crest.
Inspect moving eye-level and aerial contact through multiple wave periods.

**Transfer:** Reverse a component's direction and add an oblique component.
Which one is incoming at each boundary? Where does the selected depth band
exclude it? A seam fade alone is not evidence of a matched solution.

<details>
<summary>Hint 1: share the cause, not just the picture</summary>

Borrow SeaSurface's actual `h0` spectrum (Chapter 29 section 7), not a
look-alike. Its choppy displacement maps do not uniquely describe
direction-resolved depth-integrated transport.

</details>
<details>
<summary>Hint 2: preserve frequency across depth changes</summary>

For each component solve `omega^2=g*k*tanh(k*d)` at the boundary depth while
preserving tangential wave number. Linear continuity, `d(eta)/dt + div(q) = 0`,
then gives a progressive wave's transport `q = eta*omega*k/|k|^2`.

</details>
<details>
<summary>Hint 3: the outgoing characteristic belongs to the interior</summary>

Combine the target's incoming characteristic with the interior's outgoing
one. A relaxation strip can absorb residual reflection, but its mass source
belongs in the ledger and its reflection still needs measurement.

</details>
<details>
<summary>Worked solution: explicit band, characteristic boundary and publication</summary>

The gentle first delivery admits offshore `k<=0.15 rad/m` (wavelengths of
about 42 m and longer), then checks each refracted mode for at least sixteen
cells per wavelength and `kd<=0.5`. The second test exists because shallow
water has no dispersion: every wave travels at `sqrt(g*d)`, while a real wave
travels at `sqrt(g*tanh(kd)/k)`. Their ratio exceeds one by
`sqrt(kd/tanh(kd))-1`, about 4.02% at `kd=0.5`, so admitted crests run at most
about 4% fast. Only components whose wave vector has a negative x component
(`k.x < 0` in `ShorelineIncident.comp.glsl`) are admitted at all, so a
component reversed along x is not injected. The dispersive solver
(`ShorelineDispersion.h`, `ShorelineDisperse.comp.glsl`) is an experiment, off
in the delivered scene (`CoastalArea::FLOW_DISPERSION` is false); it does not
waive this limit.

`ShorelineIncident.comp.glsl` precomputes the admitted modes of the actual
`h0` at the fixed boundary locations. Each RK stage advances them at its
physical time.
Because the sea's inverse FFT is unnormalized and its height field is real,
one `h0` component contributes `2*Re(h0*exp(i*(dot(k,x)-omega*t)))`;
there is no additional division by FFT resolution squared. Derive reference
depth-averaged velocity from the linear transport, then form `q=hLocal*u`
through the local target column. Passing finite reference transport directly
through a nearly dry column creates arbitrarily large velocities; this failed
approach is retained in the decision log in [REFERENCE.md](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/REFERENCE.md).

The boundary combines **carried boundary values**, rather than section 0's
wave speeds. Let `un` be velocity along the outward face normal, and let `Z`
be the effective positive dimensionless impedance factor.
[IncomingBoundary](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/Demos/Horizon/ShorelineBoundary.h)
validates its finite positive argument;
[shoreIncoming](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Shaders/Shoreline/ShorelineSampling.glsl) uses
`max(target.w,0.1)`. They retain
`out = unInterior + 2*Z*sqrt(g*hInterior)` and take
`in = unTarget - 2*Z*sqrt(g*hTarget)`. They recover
`un = (out+in)/2`, `c = max(0,(out-in)/(4*Z))`, then `h = c*c/g`.
The tangential velocity comes from the target for inward reconstructed flow,
otherwise from the interior; transport is `h*velocity`.

For `Z=1` in the one-dimensional homogeneous shallow-water model, the distinct
`un±2*sqrt(g*h)` combinations are the classical
[shallow-water Riemann invariants](https://www.clawpack.org/riemann_book/html/Shallow_water.html#Integral-curves).
The non-unit factor is this implementation's impedance-scaled coupling rule;
it does not prove exact matching for arbitrary flow. Identical still columns
with `h=1` and `Z=1` must reconstruct the same depth. Substituting the earlier
wave-speed values `±sqrt(g)` into this reconstruction would instead produce
`h=0.25`. Keep that neutral arithmetic check before measuring a forced wave.

Two ghost layers outside the domain give MUSCL reconstruction its two-cell
stencil at the edge. Inside, a twelve-cell relaxation strip nudges submerged
cells toward the incident target, with a weight that falls quadratically away
from the edge. The strip applies an explicit, ledgered source; it is not a
replacement for testing reflection. The CPU suite's `OpenWaveBoundary` test
does that on a flat 2 m channel: it fits two gauges to the forcing frequency,
separates incoming from reflected waves, and requires incoming gain within
5%, reflection under 5% and phase within 0.05 rad, with the volume ledger
closed to 1e-10. Finite-depth linear extension over shallow lateral
boundaries is an approximation, not calibrated run-up data.

Before a new state is published, a diagnostics pass reduces the whole field
on the GPU to its volume, ledger terms and failure flags. One flag anywhere
keeps the last valid field visible instead of publishing a mixture of good
and bad cells. `SurfaceFields` reads only valid current/previous publication;
SeaSurface keeps the sole water draw. Replace the local low-frequency
geometry rather than adding it to the full FFT. Derive bulk normals from the
final surface. Unresolved normal detail,
opaque-scene transmission and wet-sand contact require their own graphics
checks; this numerical coupling exercise does not imply those are finished.

</details>

## 5. Remember Where Water Has Been

<a id="ch43-wet-history"></a>

### Attempt CH43-wet-history: leave wet sand after retreat

Make the shore darken only after inundation. When the front retreats, retain
history which dries with a declared time constant. Camera movement, a dry
low spot and toggling a diagnostic view must not repaint the coast.

**Acceptance:** The actual surface compute shader sets history to one under
water, retains `exp(-12.5/25)` after 12.5 dry seconds, clears on reset, and
keeps never-inundated cells at zero. Inspect a retreating sequence, not only a
still image while the water is advancing. Submerged seabed must not change
material merely because it crosses the atlas boundary; inspect from offshore
too. Material response and history state are separate choices.

**Transfer:** Pause for ten wall-clock seconds. Does the shore dry? Then
single-step. Specify whether drying follows physical time or wall time before
comparing the pictures.

<details>
<summary>Hint 1: distance from sea level is not history</summary>

A constant height stripe cannot distinguish untouched sand from recently
retreated water, nor can it respect a dry ridge around an isolated pit.

</details>
<details>
<summary>Hint 2: decay should compose across time steps</summary>

Express the decay with a time constant in seconds (25 s in the acceptance).
Repeated multiplicative decay should give the same answer when a time
interval is split into smaller intervals.

</details>
<details>
<summary>Hint 3: keep the field in world space</summary>

Store history with the fixed physical cells, not screen pixels or camera
tiles. Ground shading samples its own world position in the same atlas.
After retreat, a water-only overlay has no coverage on exposed sand; the
ground pass must participate in inspecting that history.

</details>
<details>
<summary>Worked solution: state first, material response second</summary>

The first of the three operations in `ShorelineSurface.comp.glsl`
(`surface.operation == 0`) reads published, time-interpolated depth and
updates the persistent R32F cell field. `surface.dt` is the change in display
time, which holds still while paused, so history follows physical time:

```glsl
float old = surface.resetHistory != 0u ? 0.0 : imageLoad(wetHistory,p).r;
float wet = displayedState(i).x > 0.0001 ? 1.0 : old*exp(-surface.dt/25.0);
imageStore(wetHistory,p,vec4(wet));
```

Operation 1 then averages the four cells around each node into the alpha
channel of the node atlas, already multiplied by the rim weight.
Terrain has one optional, always-valid descriptor and an explicit wetness
enable flag; noncoastal ground does not read the live coastal field. Bind the
borrowed atlas before first use or at an idle recreation boundary, not by
updating an in-flight descriptor on every viewpoint selection.

That is not yet a complete material handoff. Applying darkening only inside
the physical box makes a rectangular patch visible through clear water:
the surrounding submerged seabed was still shaded as dry. Reading the whole
sixteen-cell atlas rim removes the hard cutoff but does not fix that baseline
mismatch. `ShorelineWetMaterial.glsl` combines the atlas's already-weighted
history with `(1-weight)*farImmersion`. Do not weight its alpha a second time.
Inside the physical domain the weight is one: only real history counts, so an
FFT crest cannot mark a never-flooded pit. Outside, terrain samples the actual
three ocean displacement maps and real cascade parameters, using two bounded
inverse steps for horizontal chop. This supplies current offshore immersion,
not persistent drying or numerical run-up outside the simulated domain.

The three borrowed sampled images and a terrain-owned 32-byte parameter UBO
have valid neutral bindings. Ocean displacements start cleared/readable even
when the sea is hidden at startup; their write/read barriers include terrain
fragment reads. The `geometry-only` mode of `TutorialShorelineGpuTests` (its
fourth argument, after the GPU name, an output folder and the solve-iteration
count) checks the shared material blend and an actual filtered FFT fixture as
well as geometry. The `material-broken` and `material-rim-broken` modes
restore the mismatched baseline and clipped atlas read, respectively, and
must fail the named material handoff check. These small
oracles still require an offshore moving-camera image check.

The first material response is authored albedo darkening, not a complete
water-film BRDF or calibrated sand reflectance. It cannot create history by
itself. `SurfaceHistoryControls` executes the production shader and reads the
real persistent image after inundation, retreat and reset. The ready source
is not a CPU-only imitation of that equation. The history currently follows
the presented published state; sub-frame inundation which begins and ends
between presentations is not a separately resolved wetting event.

The Coastal view selector's Wetness mode shows the same actual history on
water and exposed physical ground, with one shared color map. The selector
uses a previously reserved push-constant word without growing `TerrainDraw`.
It is an unlit diagnostic after haze, not a change to water state or material
response. Normal rendering remains separate. Run the paired wet-history
smoke in this mode, then return to Water to judge the final material.

</details>

## 6. See The Bed Without Reading An Active Attachment

<a id="ch43-opaque-water-inputs"></a>

### Attempt CH43-opaque-water-inputs: preserve opaque geometry before water

Show the bed through shallow water using the host's opaque HDR color and
depth. Keep grass, objects, reversed depth and MSAA correct. Predict what
happens if water samples the color or depth attachment it is currently writing.

**Acceptance:** The offscreen oracle preserves both untouched color and depth
across a loaded scene continuation at 1x and 4x. A snapshot remains unchanged
when later water-side rendering changes the scene. With one near MSAA sample
at reversed depth .75 and the others at .25, refraction sees the closest .75
while conservative host Hi-Z keeps its independent farthest-depth policy.
Inspect shallow/grazing contact, foreground rejection, resize and recreation.

**Transfer:** Replace reversed depth by conventional depth on paper. Which
resolve becomes closest? Explain why the same fixed MIN operation cannot serve
both conventions and both occlusion and refraction policies.

<details>
<summary>Hint 1: split ownership, not the world</summary>

The host still owns one camera, sky, opaque scene and set of targets. A
second rendering scope is a resource handoff, not another demo or renderer.

</details>
<details>
<summary>Hint 2: resolved and multisampled images have different lifetimes</summary>

A resolved image does not preserve the MSAA attachment after a DONT_CARE
store. Keep the opaque multisampled color and depth until the loaded water
scope has consumed them.

</details>
<details>
<summary>Hint 3: reject invalid refracted hits</summary>

Reconstruct world position using the same inverse view-projection and Vulkan
depth convention. Sky depth, offscreen coordinates and geometry above water
are not a valid underwater path. Linear filtering of a depth format is an
optional format feature, so do not assume it.

</details>
<details>
<summary>Worked solution: owned snapshots, closest depth and shared lighting</summary>

`OpaqueInputs` owns window-sized HDR and depth images. After the host draws
opaque terrain, objects and grass, it ends the preserved scene scope. At 1x
the owner copies resolved color and depth. At MSAA it copies resolved color
and resolves preserved MSAA depth with MAX into its own depth image. The
host's MIN depth resolve remains available for conservative reversed-depth
Hi-Z. The owner checks MAX support; it does not silently label sample-zero
depth as closest depth. Point sampling avoids assuming linear-filtered depth.

The source attachments return to attachment layouts; the owned inputs become
shader-readable. `beginScenePass`'s opt-in loaded continuation keeps opaque
color/depth and draws water. The original four-argument API retains its old
clear/discard behavior for other demos. Resize and MSAA recreation rebuild
descriptors at the host's existing idle boundary. An ordinary resize keeps the
water state; changing the sample count sets the whole demo up again (Chapter
18 section 7), which resets the water to its initial state. The complete
methods are in
[ShorelineOptics.cpp](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/Demos/Horizon/ShorelineOptics.cpp)
and [SceneTargets.cpp](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/VulkanGraphics/SceneTargets.cpp).

The coastal shader estimates a refracted path with water IOR 1.333, rejects
above-water/offscreen hits, attenuates the background with Beer-Lambert
absorption and adds the water-body fallback. It removes the same host aerial
haze from the opaque input before applying underwater absorption and final
water-to-eye haze. This is a bounded screen-space approximation, not layered
ray tracing, underwater rendering or offscreen terrain reflection.

Closest MSAA depth can come from a different covered sample than the pixel
centre used for reconstruction. At the original pixel only, compare projected
reversed depth with a tolerance of one pixel's depth footprint
(`fwidth(gl_FragCoord.z)`) plus four float ULPs of that depth
(`seaContactDepthTolerance` in `SeaTransmission.glsl`); do not turn this into
a fixed world-space stripe. World-height tolerance alone did not bound the
perspective/MSAA mismatch in the native controls. Refracted offset samples
retain strict above-water rejection. A thin accepted path transmits the
source bed rather than selecting the deep-water fallback. Compare 1x and 4x
contact explicitly: a clean offscreen snapshot test alone missed this failure
in the first native captures. Resolved colour is still an MSAA
approximation, not sample-exact transmission.

The engine's scene depth is always `D32_SFLOAT` (Chapter 10 fails startup
without it), so a D16 target reaches this code only from the optics test
fixture; the shader still handles one. The D16 path adds its actual `1/65535`
depth quantum to this bound; D32 does not inherit that larger allowance. The
offscreen optics oracle exercises real D16 and D32 snapshots at 1x/4x, while
the shared-predicate oracle checks quantized contact and rejects a foreground
hit beyond that precision bound. D16's larger uncertainty is not equivalent
to D32-quality refraction.

Direct reflection uses the existing shared GGX implementation (Chapter 15).
Sky reflection uses the existing prefiltered environment and BRDF LUT
(Chapter 24). Do not add the old Phong sun glint on top of GGX or multiply its
Fresnel twice. Derive bulk normals from final geometry, add only unresolved
FFT slopes, and inspect normal-driven specular aliasing at grazing angles.
The legacy Sea demo retains its taught shader route; the coastal
specialization supplies these additional resources.

</details>

## Exit Checks

Run the CPU suite (`TutorialShorelineTests`), then the small GPU controls
(`TutorialShorelineGpuTests`, one mode at a time) on each device with
validation. Compare actual fields and ledgers, including nonzero boundary
forcing and deliberately exhausted retry budgets. Run Horizon at a coastal
viewpoint for at least five minutes of simulated time; the reference's
acceptance run is 300 s on both GPUs. Record both numerical errors and
chronological cost; short early windows can miss a later advancing-front
failure.

Then inspect shore, aerial and moving captures with all intended foliage.
Repeat pause/reset, 30/60/144 Hz presentation, resize/MSAA and demo switching.
A clean validation log and a nonblank image are necessary, not sufficient.
Use [REFERENCE.md](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/REFERENCE.md) for measured results and outstanding
checks. Persistent wetness here is authored albedo darkening, not a calibrated
wet-film BRDF; the chapter does not promise calibrated bores or surf foam.

Next on the written graphics continuation: [46 — Capturing Grass Clumps](46-Capturing-Grass-Clumps.md),
then 47 and 48. Their grass prerequisites include 27 and 41; Chapter 48 uses
this shoreline. Surf and Sand (44) remains planned. [Chapter 45](45-Scene-Documents-And-Properties.md)
is the separate scene-project route after 19, not a prerequisite for grass.
