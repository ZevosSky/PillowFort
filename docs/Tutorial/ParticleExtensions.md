# Particle extension labs

Chapter 21 supplies a small working GPU particle owner. These optional labs
grow one mechanism at a time, using that existing owner instead of requiring
an effect graph or a general renderer rewrite. Basic graphics and linear
algebra are assumed.

The [wind-field continuation](52-Wind-Fields-And-Vorticles.md) has an authored
reference implementation and numerical targets. The four labs here are design
briefs for reader implementations, not completed features or prepared
Starter/Solution exports. Consult [current project status](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/ROADMAP.md#status) and
[guarded wind test commands](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Tests/TutorialHarness/README.md#particle-wind-checks)
for the current evidence boundary.

Start with [ParticlesDemo.cpp](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Source/PillowFort/Demos/Particles/ParticlesDemo.cpp),
[ParticleTypes.h](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Shaders/Particles/ParticleTypes.h) and the
[particle shaders](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Shaders/Particles/ParticleEmit.comp.glsl). Keep one
small lab per branch or commit so its neutral control stays easy to reproduce.
Try Lab 1 first if you want the smallest addition; choose one lab at a time.
The particle pool remains persistent. Only CPU upload snapshots use frame
slots; checked writes occur after that slot's fence and before submission.

## Lab 1 — emit over an area

**Produce:** a disk fountain with the same initial speed/direction distribution
as the point fountain. Change only the birth position first.

Edit the emitter controls and `ParticleSimulation` initialization in
`ParticlesDemo::RecordCompute`, then the initial position in
[ParticleEmit.comp.glsl](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Shaders/Particles/ParticleEmit.comp.glsl).
`emitterPosition.w` is currently unused and can become a documented radius in
metres; this keeps `ParticleSimulation` at 96 bytes. Update its shared comment
and validate a finite nonnegative radius on the CPU. In the assembled reference,
or when retaining Chapter 52, wind count/rate occupy offsets 84/88. A baseline
21 implementation should reserve or isolate that interface before combining
these extensions; those words are not shared free space.

For a disk in the XZ plane, two uniform samples `u,v` in `[0,1)` give:

```text
r = radius * sqrt(u)
angle = 2*pi*v
position = emitterCenter + (r*cos(angle), 0, r*sin(angle))
```

Derive a separate shape random stream from the existing birth seed without
advancing the stream used by `randomInCone`, speed or lifetime. For example,
hash the seed with a fixed shape salt into a second local state. Otherwise
adding position randomness also changes every existing velocity/lifetime,
making the comparison harder to interpret. Radius zero should take the point
path without adding offsets.

**New contract:** uniform radius is not uniform area. Birth random dimensions
have deliberate roles. Cost grows with emissions, not with all living particles.
No buffer, descriptor or simulation pass is added for this lab.

**Acceptance, before the picture:** `u=0.25,v=0` lands at `radius/2` along +X;
all samples stay inside the disk; radius zero preserves a fixed single birth's
position, direction, speed and lifetime. Over 65,536 deterministic samples,
about one quarter should lie within half radius; a one-percent absolute
population tolerance distinguishes this from the incorrect uniform-radius
result near one half. That histogram is a practical distribution check, not a
proof that a pseudo-random stream is independent. Particle ownership/count
checks from Chapter 21 must still hold.

**Transfer:** orient the disk with an emitter basis, then put it on a surface.
That adds an orientation contract and eventually a surface-area distribution;
it does not change the dead/alive pool protocol.

## Lab 2 — several emitters share one bounded pool

**Produce:** two differently placed emitters whose combined births cannot
overdraw the free slots. Keep common particle appearance and forces at first,
so the existing 32-byte particle record can remain unchanged.

The exact edits are the CPU emission scheduling in `RecordCompute`, the GPU
allocation in [ParticleBegin.comp.glsl](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Shaders/Particles/ParticleBegin.comp.glsl),
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

The begin pass already knows `deadCount`; give its single invocation this job:

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

**Produce first:** a three-key size curve using normalized age, with exact
chosen values at birth, midpoint and death. Edit only
[Particle.vert.glsl](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Shaders/Particles/Particle.vert.glsl) before changing
the draw resources. The current shader already computes normalized `life`,
linear size/color and an opacity fade. Choose whether the new curve replaces
size interpolation or also changes opacity; keep those decisions explicit.

A piecewise analytic curve with fixed keys needs no new buffer. Editable keys
need declared appearance parameters and layout checks. `ParticleAppearance`
currently occupies 48 bytes, and the fountain's fragment push constant follows
it. [ParticleSoft.frag.glsl](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Shaders/Particles/ParticleSoft.frag.glsl)
currently names offset **48** explicitly. Enlarging the appearance block means
updating that offset, both push ranges and all `vkCmdPushConstants` calls,
while keeping the total within the queried push-constant limit. The sea spray
also reuses `ParticleAppearance` and `Particle.vert`; either preserve its neutral
defaults or introduce a deliberate fountain-specific shader/type variant.

**Acceptance:** evaluate the curve at `life=0,0.5,1` and just either side of a
key. Check continuity, finite nonnegative size, and pause. Restoring the original
linear curve must recover the declared neutral result. This appearance change
must not alter the particle pool or counter readbacks.

**Then produce:** a flipbook from one fixed atlas. Pass UV/frame information
from the vertex shader and sample it in the fragment shader actually selected
by the fountain: `ParticleSoft.frag.glsl`, not just `Particle.frag.glsl`.
Preserve its optional depth intersection fade. Add a new sampled-image binding
and descriptor pool count; binding 5 is already the depth sampler. A one-atlas
first version avoids descriptor-array indexing and per-particle texture IDs.

For `N` frames and clamped normalized age, use
`frame = min(floor(life*N), N-1)`. Declare whether the atlas is straight-alpha
or premultiplied and perform premultiplication once. Insets/padding are a
filtering contract, especially with mipmaps. Additive dots do not establish
correct ordering for alpha sprites; retain additive blending first, then
consider sorting or an order-independent method as a separate renderer change.

**Acceptance:** a diagnostic atlas with numbered colored frames selects the
first, middle and last frames at prescribed ages; the final age never samples
frame `N`. Adjacent cells do not bleed at the chosen filtering/mip settings.
The untextured control and zero soft-distance path remain available. Inspect
overlapping sprites separately from atlas indexing.

**Transfer:** a curve controls a lifetime response; a flipbook controls sampled
appearance. Neither implies a new particle simulation or a new owner per sprite.

## Lab 4 — separate trail history from collision geometry

Choose **one** of these continuations first. Both affect particle motion's
observable result, but they require different state and cannot be completed by
changing the current billboard fragment shader.

**Trail route:** add a bounded history/metadata buffer alongside the persistent
pool in `ParticlesDemo::CreateBuffers`, initialize new-birth identity in the
emit pass, write samples after integration in
[ParticleSimulateBody.glsl](https://github.com/ZevosSky/PillowFort-private/blob/reference-main/Shaders/Particles/ParticleSimulateBody.glsl),
and generate/draw segments through a new pass/pipeline. Decide whether the
shared body should affect sea spray or whether only the fountain wrapper opts
in, as the wind wrapper does. Source history ownership must survive draw-list
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
choose heightfield, screen depth, SDF or mesh collision. A heightfield cannot
observe overhangs; camera depth cannot observe off-screen geometry. Each new
representation needs its own resources and synchronization.

## Larger continuations

After the bounded [vorticle lesson](52-Wind-Fields-And-Vorticles.md), consider
GPU-authored wind events, source spatial bins, fixed-step budgets, camera-follow
ambient populations, or shared wind across vegetation/cloth. The first sampler
is linear in particles times sources; a spatial accelerator must preserve every
overlapping source's support and zero exterior before its timing matters.

For foliage scale and batches, continue through Chapters
[19](19-Instancing-And-Indirect.md), [37](37-Objects-At-A-Distance.md) and [39](39-Plants.md).
Keep per-instance pose/scale separate from shared source geometry and material
resources. Deformation must reach culling and shadow bounds. Shared wind input
does not require a shared response law: particles can relax velocity while
plants derive displacement and stiffness. Full GPU effect graphs, general
collision and trail renderers remain larger systems with their own ownership,
capacity and evidence requirements.
