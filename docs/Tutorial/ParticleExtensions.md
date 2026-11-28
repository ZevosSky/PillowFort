# Particle extension labs

Chapter 21 supplies a small working GPU particle owner. These optional labs
grow one mechanism at a time, using that existing owner instead of requiring
an effect graph or a general renderer rewrite. Basic graphics and linear
algebra are assumed.

The [wind-field continuation](52-Wind-Fields-And-Vorticles.md) and
[Chapter 54 — Shaping a Particle Effect](54-Shaping-A-Particle-Effect.md) and
[Chapter 55 — Sorted Smoke](55-Sorted-Smoke.md) have authored reference
implementations. The five labs here are design briefs for reader
implementations, not completed features or prepared Starter/Solution exports;
Lab 1 and the first half of Lab 3 point to Chapter 54, and the second half of
Lab 3 to Chapter 55, which build them, and keep only what they do not. Consult current project status (the reference's `ROADMAP.md`, section "Status") and
guarded wind test commands (the reference's `Tests/TutorialHarness/README.md`, section "Particle wind checks")
for the current evidence boundary.

Start with `Source/PillowFort/Demos/Particles/ParticlesDemo.cpp`,
`Shaders/Particles/ParticleTypes.h` and the
particle shaders (`Shaders/Particles/ParticleEmit.comp.glsl`). Keep one
small lab per branch or commit so its neutral control stays easy to reproduce.
Choose one lab at a time.
The particle pool remains persistent, one copy for both frames in flight. Only
CPU upload snapshots (Chapter 10's frame data, with Chapter 52 its wind
sources, and with Chapter 54 the look's staging buffers) and the counter
readbacks use frame slots; a lab that adds a per-frame
upload writes it, checked, after that slot's fence and before submission.
A pass a lab adds is either declared, as in
[Chapter 57](57-The-Frame-Declared.md), or recorded with its barriers by hand,
as on the hand-written route.

**The starting point.** The labs and the links above describe the assembled
reference: Chapter 21 with its section 9 soft particles, plus Chapter 52's
wind and Chapter 54's shapes, clock, prewarm and look curves. With Chapter 21
alone every lab still applies, with three differences:
the whole simulation is in `ParticleSimulate.comp.glsl` (Chapter 52 moves its
body into `ParticleSimulateBody.glsl`, an include shared by two wrappers);
without section 9's exercise the fountain draws with `Particle.frag.glsl`,
has no fragment push constant, and its particle set has no binding 5; and the
`ParticleSimulation` words and compute set that Chapters 52 and 54 take are
still free. With Chapter 21 alone, the words at 84, 88 and 92 and
`emitterPosition.w` are free; 52 takes 84 and 88, 54 takes 92 and `w`. Reserve
them before combining labs with Chapter 52 or 54.

## Choose by mechanism

Pick an extension by the mechanism it adds, not by the effect's name: the same
look can need very different state. Each row names the lab that carries it.
[Chapter 52](52-Wind-Fields-And-Vorticles.md#4-choose-the-next-extension-by-its-hidden-mechanism)
keeps the three rows that need its wind sources: moving or expanding
vorticles, GPU-emitted sources, and fixed-step simulation.

| You want | The mechanism it adds | Where |
| --- | --- | --- |
| A disk, a ball or a box | Area and volume sampling that is uniform per area or volume | [Chapter 54, section 2](54-Shaping-A-Particle-Effect.md#2-births-on-a-shape) builds them; [Lab 1](#lab-1--emit-over-an-area) keeps what it leaves |
| Several fountain emitters | Stable emitter identity and a bounded share of the free slots, instead of a reused slot standing for a birth | [Lab 2](#lab-2--several-emitters-share-one-bounded-pool) |
| Curved size, color and glow | A response over normalized age with explicit units, baked into an image | [Chapter 54, sections 5 and 6](54-Shaping-A-Particle-Effect.md#5-curves-baked-into-an-image) |
| Nonuniform forces | Forces go in the shared integration body, `ParticleSimulateBody.glsl` with Chapter 52 or `ParticleSimulate.comp.glsl` without it; give each force its units, check it under pause, and run it at two time steps, because a force applied once per frame changes with the step | A brief, here |
| Sprite and flipbook particles | A sampled atlas, frame selection by age, an alpha convention and atlas padding, with the optional depth fade kept | [Chapter 55, section 5](55-Sorted-Smoke.md#5-a-flipbook-baked-in-compute) builds it; [Lab 3](#lab-3--change-the-lifetime-shape-then-add-a-flipbook) keeps the brief |
| Other facings and age orders | A vertex-shader frame per facing, and the key it allows; a key per order; 55's network and Check order unchanged | [Lab 5](#lab-5--face-another-way-or-order-by-age) |
| Trails | Bounded history owned by a stable birth identity, and a new segment draw | [Lab 4, trail route](#lab-4--separate-trail-history-from-collision-geometry) |
| Terrain and scene collision | A collision representation of its own, with a stated limit on what geometry it can observe | [Lab 4, collision route](#lab-4--separate-trail-history-from-collision-geometry) |
| Shared wind for batched foliage | One field feeding many instances, with deformation reaching culling and shadow bounds | [Larger continuations](#larger-continuations), after Chapter 52 |

## Lab 1 — emit over an area

**Built by Chapter 54.** [Chapter 54, section 2](54-Shaping-A-Particle-Effect.md#2-births-on-a-shape)
builds this lab and more: a disc in the XZ plane (and a ball, a sphere's skin
and a box) whose births are even per area, drawn from a second, salted random
stream so that the speed, direction and lifetime of every particle stay as
Chapter 21's stream gives them, with a size of zero taking the point path
exactly. Its size is `emitterPosition.w` and its kind is the word at byte 92,
`emitterShape`; words 84 and 88 are Chapter 52's. Its checks are the lab's: a
quarter of the births within half the radius, none outside, and births moved,
nothing else.

What it does not build is this lab's brief now: give the disc an emitter basis
so it can face any way, then put it on a surface. That adds an orientation
contract and eventually a surface-area distribution (Chapter 21's
[Where to go from here](21-GPU-Particles.md#where-to-go-from-here) sketches the
mesh case).

**Transfer:** neither orientation nor a surface changes the dead/alive pool
protocol.

## Lab 2 — several emitters share one bounded pool

**Produce:** two differently placed emitters whose combined births cannot
overdraw the free slots. Keep common particle appearance and forces at first,
so the existing 32-byte particle record can remain unchanged.

The exact edits are the CPU emission scheduling (in the assembled reference,
`EmissionSchedule` and `ParticlesDemo::RecordStep`), the GPU
allocation in `Shaders/Particles/ParticleBegin.comp.glsl`,
birth lookup in `ParticleEmit.comp.glsl`, and shared allocation types in
`ParticleTypes.h`. Do not run the current begin pass independently for each
emitter: it resets the next alive list and computes totals for one request.

Start with at most eight CPU emitter records. Each has stable emitter identity,
its own fractional emission carry, a requested count, and a first birth ordinal.
Upload a fixed-size emitter block per frame slot through its own compute UBO
set or a new uniform binding. Account for its descriptor pool entries and
pipeline layouts explicitly. When retaining Chapter 52, its wind UBO occupies
compute set 1, binding 0; reserve a different interface for the emitter block.
The baseline 21 reader must make that allocation explicit before combining
the lessons. The base particle owner still needs five storage descriptors. Adding
a sixth storage buffer requires another capability check, not an assumption.

A small allocation table can instead be appended to the **existing** indirect
storage buffer at binding 4. Preserve command offsets 0, 12 and 24. One explicit
layout is eight 16-byte allocation records starting at byte 48, after eight
bytes of padding; the whole `ParticleIndirect` then occupies 176 bytes. Update
allocation sizes and C++/GLSL size/offset assertions together. Vulkan's actual
dispatch/draw command records and offsets remain unchanged.

The begin pass already knows `deadCount`; give its single invocation this job.
[Chapter 21's sketch](21-GPU-Particles.md#where-to-go-from-here) builds the
same table with one invocation per emitter and a running total, clamped on the
total; a single invocation walking the emitters in priority order is the
simpler serial form for a few emitters, and it states which emitter loses when
the pool is short:

```text
remaining = deadCount; prefix = 0
for emitter in a documented priority order:
    accepted = min(requested[emitter], remaining)
    plan[emitter] = (prefix, accepted)
    prefix += accepted
    remaining -= accepted
emitCount = prefix
write ONE emit dispatch and ONE simulate dispatch from these totals
```

One emission invocation finds the nonempty interval containing its global ID,
then uses the emitter's parameters and its local birth ordinal. Existing
dead-list pops and current-alive appends still happen once per accepted birth.
The existing begin-to-emit storage/indirect dependency must cover the appended
table too.

**New contract:** this priority allocator can starve later emitters when the
pool is full. State that policy; weighted or rotating fairness is a later
change. This lab keeps only fractional carry and drops denied whole births.
Assign birth ordinals to **requested** births on the CPU: a request of five
advances that emitter's ordinal by five even if only two fit. The three denied
ordinals remain unused. This makes the next request independent of delayed
GPU readback. Advancing only by accepted births would instead need persistent
GPU ordinal state or a declared readback/publication protocol; it is a different
extension. A bounded backlog would also need a different emission policy.

An emitter array index is not stable identity. Seed from emitter identity plus
its requested-birth ordinal if reordering must preserve its random stream;
detect counter exhaustion before publication or use a two-word ordinal rather
than silently wrapping. Saving
those identities in each particle is only necessary when later consumers need
them; this first lab may use them solely at birth.

**Acceptance:** requests `(4,5)` with six free slots yield accepted `(4,2)` and
intervals `[0,4)`, `[4,6)`; global ID 4 belongs to the second emitter at local
ordinal zero. With starting ordinals `(100,200)`, accepted births use
`100..103` and `200..201`, while the next CPU ordinals are `(104,205)`.
Even a fully denied nonzero request consumes its requested ordinals; a zero
request consumes none. Empty intervals receive no invocations. Sum accepted births never
exceeds free slots. Zero emitters preserves the living pool without resetting
it. Reorder records while retaining IDs and check the declared random-stream
policy. Compare live/dead ownership, not just the sum of counters.

**Transfer:** several emitters can share a pool just as compatible foliage
instances share geometry/resources. Per-emitter initial conditions are separate
from per-particle state and from resource-compatible draw batches.

## Lab 3 — change the lifetime shape, then add a flipbook

**Built by Chapter 54.** [Chapter 54, sections 5 and 6](54-Shaping-A-Particle-Effect.md#5-curves-baked-into-an-image)
build the first half of this lab, and more: size, color and glow as curves of
at most eight keys over normalized age, baked into a 256-texel image that
`ParticleCurves.vert.glsl` reads with one filtered fetch, and rewritten inside
the frame when a key is edited. Its checks are the lab's, with the same
neutral control: a two-key curve and a glow of 1 reproduce Chapter 21's linear
mix. Chapter 54 draws the curves with its own vertex shader so that the sea's
spray keeps `ParticleAppearance` and `Particle.vert` as they were.

**Built by Chapter 55.** [Chapter 55, section 5](55-Sorted-Smoke.md#5-a-flipbook-baked-in-compute)
builds the second half of this lab: one fixed flipbook atlas, baked once in
compute, with the frame picked from the particle's age and the frames at both
ends of a life attempted and checked there. Additive dots do not need an
order; alpha sprites do, and
[Chapter 55, section 3](55-Sorted-Smoke.md#3-the-sort-on-the-gpu) sorts them.
The brief that is left is a different atlas, or a second one: keep the frame rule, declare whether the atlas is straight-alpha or
premultiplied and premultiply once, and inset every cell so the filter cannot
reach its neighbour.

**Acceptance:** for the new atlas, every cell the frame index names is a cell
of the particle's own shape at every life, life 1 shows the last frame with
nothing blended past it, and a filtered read anywhere in a cell's content takes
nothing from a neighbouring cell. Check the first two and each cell's border on
the CPU, as Chapter 55's supplied test does, and argue the filter's reach from
the border's width, as its section 5 does. Paused, the effect stands still, and
no puff has a dark rim.

**Transfer:** a curve controls a lifetime response; a flipbook controls sampled
appearance. Neither implies a new particle simulation or a new owner per sprite.

## Lab 4 — separate trail history from collision geometry

Choose **one** of these continuations first. Both affect particle motion's
observable result, but they require different state and cannot be completed by
changing the current billboard fragment shader.

**Trail route:** add a bounded history/metadata buffer alongside the persistent
pool in `ParticlesDemo::CreateBuffers`, initialize new-birth identity in the
emit pass, write samples after integration in
`Shaders/Particles/ParticleSimulateBody.glsl`
(with Chapter 21 alone, in `ParticleSimulate.comp.glsl`),
and generate/draw segments through a new pass/pipeline. Decide whether the
shared body should affect sea spray or whether only the fountain wrapper opts
in, as Chapter 52's wind wrapper does. Before Chapter 52 there is no wrapper:
Chapter 31's spray dispatches the same `ParticleSimulate.comp.glsl`, so a
fountain-only trail needs a variant of that shader. Source history ownership must survive draw-list
compaction. Reusing a particle slot must begin a new trail generation, not
continue the previous occupant's history.

For pool capacity `P`, at most `H` samples per particle means bounded storage
`P*H` and at most `P*(H-1)` consecutive segments before any visibility filtering.
Choose a practical separate trail budget rather than silently allocating that
worst case for a million particles. Adding metadata as a parallel buffer can
preserve the 32-byte particle ABI, but adds descriptor/limit/dependency work.
Record generation identity and sample clock explicitly; specify the dropped
sample/segment policy when full.

**Trail acceptance:** two consecutive births that reuse one slot never connect;
one live particle with three positions yields exactly two adjacent segments;
reset/pause/expiration respect the chosen history policy; segment counts never
exceed capacity. A stable event ID, not a compacted alive-list index, owns the
history. Transfer the same distinction to deferred events and readbacks.

**Collision route:** first replace the current ground plane with a single
analytic sphere in the shared integration body or a fountain-only hook. State
whether response tests the new endpoint or the swept segment; endpoint tests
can tunnel through a small sphere during a large step. Supply sphere center,
radius and response parameters through a declared compute input, not an
untracked uniform write. Check push-constant space or use a properly owned UBO.

**Collision acceptance:** a point outside and moving away is unchanged; an
inside point resolves outward without NaN at the center; a known approach has
the declared bounce/slide response; a high-speed segment demonstrates the
documented endpoint limitation or passes the swept-intersection test. Only then
choose heightfield, screen depth, SDF or mesh collision, and state which
geometry the choice can observe: a heightfield cannot observe overhangs, and
camera depth cannot observe off-screen geometry. Each new representation needs
its own resources and synchronization.

## Lab 5 — face another way, or order by age

[Chapter 55](55-Sorted-Smoke.md) builds one facing, Chapter 21's camera plane,
and one order, back to front by view depth. A camera-plane quad lies in a plane
of constant view depth, so a ray meets the quads in the order of their view
depths: that is why view depth is an exact key for them, and the sort is right
from any view. This lab changes one of the two, and the reference has no code
for it: it is a brief, like the others here.

**Produce:** one facing or one order, chosen by mechanism, not both.

- A facing changes the vertex shader's frame, the two axes the quad is built
  from, and with it what the key can promise: view depth stays exact only while
  every quad lies at one view depth. Each facing below says what it does to the
  key.
- An order changes only the key function the sort reads. The network and
  Chapter 55's Check order stay as they are.

Each choice is for something, and has one thing that makes it hard.

- **Along velocity.** For sparks, rain and tracers: a streak that lengthens
  with speed, its length the size plus a stretch times the speed along the unit
  velocity, its width along the unit velocity crossed with the eye direction.
  Hard: coming straight at the camera, that cross product collapses. Blend back
  to camera-plane facing as its length goes to zero, or the streak thins to a
  flickering line. Key: a streak spans many depths and two can cross, so no key is
  exact; the view depth of each centre is the usual approximation, and it can
  be wrong where two long streaks overlap.
- **Upright**, turning about world up only. For flames and columns that must
  not lean when the camera pitches. Hard: seen from above, the quad goes
  edge-on and vanishes. Fade it, or blend to camera-plane facing at a steep
  pitch. Key: quads that all face the camera's forward flattened onto the
  ground are parallel. Under a level camera each lies at one view depth, and
  view depth stays exact; pitched, their exact key is the distance from the
  eye along that flattened forward, largest first, at any pitch short of
  straight up or down, where the flattened forward vanishes. (The depth
  along it with its sign holds only up to 90 degrees of pitch less half the
  vertical field of view.) Quads that each turn toward the camera are not
  parallel, and have no exact key.
- **Facing the camera's position.** For large puffs near the camera, which
  visibly swing with camera-plane facing as the view turns. Hard: the quads no
  longer lie in parallel planes, so no key is exact. The distance to the camera takes
  view depth's place as the approximation, and neighbouring quads can still
  intersect, cutting hard lines that no sort removes.
- **Flat**, fixed in the world. For ripples, shock rings and scorch on the
  ground. Hard: lying at the ground's depth, Chapter 21, section 9's soft fade
  takes it away entirely. Lift it, or turn the fade off for it. Key: flat quads
  are parallel to each other but not to the image, so view depth is wrong for
  them: a wide quad far ahead but high can cross a ray before a low quad
  nearer the camera does. A ray meets flat quads in order of their height's
  distance from the eye's height, which is their exact key, largest first.
- **Oldest first, or youngest first.** An order that does not change as the
  camera turns, so two puffs never swap and step: new over old for a trail seen
  from where it is heading, old over new the other way. Hard: the order ignores
  the view. It is right only where age order and depth order agree, and exactly
  backwards from the other side.

**Acceptance:**

- Check order still says yes. It checks that the keys are non-decreasing,
  whatever the key is.
- Paused, the effect stands still: two consecutive frames are identical.
- The mode's hard case is shown and handled, or shown and named as its limit: a
  spark coming straight at the camera is a dot; an upright flame seen from
  above; two intersecting camera-position quads; a flat ring with the fade on;
  an age order seen from behind.
- A facing sorts by the key named above for it; where that key is only an
  approximation, a view where it fails is shown and named.

**Transfer:** the sort is a network plus a key. A new order is a new key, not a
new sort, and so is a facing whose quads stay parallel to each other.

## Larger continuations

After the bounded [vorticle lesson](52-Wind-Fields-And-Vorticles.md), consider
GPU-authored wind events, source spatial bins, fixed-step budgets, camera-follow
ambient populations, or shared wind across vegetation/cloth. The first sampler
is linear in particles times sources; a spatial accelerator must preserve every
overlapping source's support and zero exterior before its timing matters.

For foliage scale and batches, continue through Chapters
[19](19-Instancing-And-Indirect.md), [37](37-Objects-At-A-Distance.md) and [39](39-Plants.md).
Keep per-instance pose/scale separate from shared source geometry and material
resources. Batch descriptor sets by compatible resources and pipeline; a
descriptor per blade is not required. Deformation must reach culling and
shadow bounds. Shared wind input
does not require a shared response law: particles can relax velocity while
plants derive displacement and stiffness. Full GPU effect graphs, general
collision and trail renderers remain larger systems with their own ownership,
capacity and evidence requirements.
