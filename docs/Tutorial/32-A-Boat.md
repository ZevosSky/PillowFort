# 32 — A Boat

**Goal:** a boat in the sea of Chapters 30 and 31. It floats on the waves,
pitching and rolling as they pass under it, moved as one rigid body by a
compute shader that reads the same water the surface is drawn from. The arrow
keys drive it: its bow throws Chapter 31's spray when it drops into a wave, it
leaves a wake of foam in Chapter 31's local foam map, and a camera can follow
it.

**ROADMAP:** step 21+ — Chapter 31's demo, grown, in `Source/PillowFort/Demos/Sea/`
with one more shader under `Shaders/Sea/`. The boat's model,
`Assets/Scenes/Boat.usda`, is there already: Chapter 31's script wrote it.

**Module:** still `pf::demos::sea`, and still Chapter 31's `SeaObjects`: the boat
is one more thing in the sea, read through the same probe set. `SeaDemo.cpp`
changes in two places, both in `Update`. The engine does not change.

**Math:** taught where it is first used — Archimedes' principle, a column at a
time (section 1); force and torque, how hard a body is to turn, and turning an
arrow into a body's own axes and back (section 2); the velocity of a point on a
turning body (section 2); turning a quaternion by a small rotation (section 2).
It assumes Chapter 10's cross product (section 8's box) and its quaternion as a
box that holds a rotation (section 3), and Chapter 21 section 3's semi-implicit
Euler and its drag as an exponential.

**Prerequisites:**

- Chapter 31, all of it, built and running. Above all: section 1 (`SeaObjects`
  and its class map), 2 (`SprayTypes.h`, `PropPart`, `LoadProp`, the props'
  pipeline, and `RecordDraw`), 3 (`seaHeight`), 4 (the probe set and its free
  binding 4, `CreateBuffersAndImages`, and step 8's hand-over to compute
  readers), 5 (the impact pass's step 1, `objectVelocity`, and the submersion's
  rise), 6 (`ObjectReadback`, `ReadResults`, `RecordSimulation`'s numbered
  steps, and the panel), and 7 (the local foam map and its stamp).
- Chapter 10 sections 3 (a `Transform`'s quaternion), 6 and 12 (the orbit
  controller, and `Select`, which changes controllers without a jump), and
  section 8's box on normals and the cross product.
- Chapter 21 section 3: semi-implicit Euler, and the exponential that closes a
  gap by a fraction every step.
- Chapter 20 section 9: reading results back without stalling, which is how the
  CPU learns where the boat is.
- Chapter 09 section 7: a frame's `deltaSeconds` is capped at a tenth of a
  second.
- Chapter 04 section 5: the three questions every barrier answers.

---

## Where this is going

```text
                                                      the boat: pitches, rolls, and heaves on the
              .  '  .                                 waves; arrow keys drive it; spray at the bow
           ~~/^^^^^^^^\~~      rock                   when it drops into a wave; a wake of foam
        ~~~~ |        | ~~~~              __[]__      fading behind it
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ ~~~\______/~~ :::::::::::::::: ~~~~~
```

Chapter 31's rock asked the sea where the water was and threw spray. The boat
asks the same question at twelve points under its hull, and the answers lift it.
It is a different kind of thing to put in the sea: the rock never moves, and
the boat is nothing *but* motion, worked out every frame from the water under it.

Chapter 31's frame, with the boxes this chapter adds marked *new*:

```text
 Chapter 30 steps 1-8: waves, FFT, maps, foam; hand-overs to VERTEX | COMPUTE       (Chapter 31 section 4)
 Chapter 30 step 9: the sky's Update
      |
  [ local foam fades ]   [ new: the boat moves, sec. 1-3 ]            SeaObjects::RecordSimulation
      |                         |
  [ impact: the water at the rock, and new: at the hull, sec. 3 ] -> requests, foam, wake
      |
  [ Chapter 21's begin, emit, simulate, end ]
      |
 Chapter 30 step 10: the scene pass: the sea, the rock, [ new: the boat, sec. 2 ], the sky
      |
  [ the spray ]
```

The chapter is in two parts:

- **Part 1, "Floating"** (sections 1-2): Archimedes' principle a column at a
  time, and the boat moved as one rigid body. It ends with the boat riding the
  waves, pitching and rolling, with nobody at the helm.
- **Part 2, "Under way"** (sections 3-4): an engine and a rudder on the arrow
  keys, spray at the bow, a wake, and a camera that follows; then the frame in
  order. It ends with the boat driven in a circle, leaving a ring of foam.

### What you are actually writing

The boat is spread over files Chapter 31 wrote, so its map is a list of what
it adds to each, and where:

| File | What the boat adds | Section |
| --- | --- | --- |
| `SprayTypes.h` | `BoatState`; the flag `SPRAY_FLAG_BOAT` | 1 |
| | `SPRAY_BOAT_SAMPLES`, and a `SPRAY_SAMPLE_COUNT` that counts them | 3 |
| `SeaObjects.h` | the "Boat" setting, `PropPart::boat`, `LoadProp`'s third parameter, `m_boatState`, `m_boatPipeline` | 1 |
| | `HandleEvent`, `Update`'s three parameters and two includes, "Follow the boat", `m_heldKeys`, `m_throttle`, `m_rudder`, `m_boat`, `m_haveBoat` | 3 |
| `SeaObjects.cpp` | `BOAT_START`; the boat's `LoadProp`; its buffer; binding 4; the boat pass's pipeline; `RecordSimulation`'s step 3; `PackSpray`'s start and flag; `Shutdown` | 1 |
| | the props' set 1, `RecordDraw`'s boat, the boat's hand-over in step 6 | 2 |
| | `HeldKey`, `HandleEvent`, `Update`'s keys and camera and panel group, `PackSpray`'s throttle and rudder, `ObjectReadback`'s second half and its copy, `ReadResults` | 3 |
| `SeaBoat.comp.glsl` | new: buoyancy, drag, and one rigid body | 2 |
| | step 2: the engine and the rudder | 3 |
| `SeaProp.vert.glsl` | the boat's state at set 1, binding 4, and its matrix | 2 |
| `SprayImpact.comp.glsl` | the boat's state, its sixteen points, step 1's `else`, the return between steps 2 and 3, the wake | 3 |
| `SeaDemo.cpp` | `HandleEvent` in `Update`'s event loop; `Update`'s call gets the camera | 3 |

Appendix A prints the three functions the boat touches in the most places,
`PackSpray`, `Update`, and `RecordSimulation`, as they end.

---

# Part 1 — Floating (sections 1-2)

Part 1 puts the boat in the sea and lets the sea move it: first the push that
holds it up, then everything that turns that push into motion.

## 1. Floating

### Archimedes, a column at a time

A body in water is pushed up by the **weight of the water it pushes aside**.
That is Archimedes' principle, and it is the whole of floating: a boat sinks
until the water it displaces weighs as much as the boat.

$$
F = \rho \, g \, V
$$

ρ is the water's density, 1025 kg/m³ for sea water; *g* is 9.81 m/s²; *V* the
volume under the water. A hull's submerged volume is an awkward shape, and it
changes every frame as the waves pass. So the hull is cut into **columns**:
twelve points spread over the bottom of the hull, each standing for 1.2 m² of
it. A column is as deep as the water above its point, so its volume is 1.2 m²
times that depth, and its push is up, at the point:

$$
F_i = \rho \, g \, A \, d_i
$$

A worked example. The boat weighs 4000 kg, `4000 × 9.81 = 39,240` N. For the
twelve columns to carry it, their depths must add up to
`39,240 / (1025 × 9.81 × 1.2) = 3.25` m: 0.27 m each, on level water. So at
rest the boat sits with its bottom 27 cm under the water. Push it down 10 cm and
every column gains `1025 × 9.81 × 1.2 × 0.1 = 1207` N, 14.5 kN in all, which
pushes it back up; lift it and it falls. A wave under the bow deepens the bow's
columns and not the stern's, and the bow rises.

A column is never deeper than the hull is high, 1.1 m: past that the deck is
under water, and a deck under water pushes aside nothing more. The depth is
also never negative: a point out of the water pushes nothing.

### The boat

The boat is `Assets/Scenes/Boat.usda`, written by the same script as the rock
(Chapter 31's Appendix B): an open boat 6.2 m long and 2.4 m wide, a hull of
seven flat side panels joined to a narrower flat bottom, a wooden deck, and a
cabin, its bow pointing along −Z. **Its origin is its centre of mass**, low in
the hull where the engine would be: the keel 0.25 m below it, the deck 0.85 m
above. Section 2 shows why that height matters.

Chapter 31's `LoadProp` loads it, once a part can say that it is the boat's:
where the boat is, the GPU decides, so its parts are drawn differently from the
rock's (section 2). `PropPart` gains a flag, after `color`,

```cpp
    bool      boat = false;           // Chapter 32 section 2: placed by the GPU's boat state, on top of `model`
```

`LoadProp` gains a third parameter, in `SeaObjects.h`,

```cpp
    InitializationResult LoadProp(const std::filesystem::path& file, const glm::mat4& placement, bool boat);   // section 2
```

and in its definition,

```cpp
InitializationResult SeaObjects::LoadProp(const std::filesystem::path& file, const glm::mat4& placement, bool boat)
```

and copies it into every part it makes, after `.color`:

```cpp
            .boat    = boat,
```

In `SeaObjects::Initialize`, the rock's call passes `false`, and the boat is
loaded after it, with no placement of its own:

```cpp
    // Section 2: the rock where SprayTypes.h says it stands. Chapter 32: the boat, where its state puts it.
    const glm::mat4 rockPlacement = glm::translate(glm::mat4(1.0f), glm::vec3(SPRAY_ROCK_X, SPRAY_ROCK_Y, SPRAY_ROCK_Z));
    if (auto result = LoadProp(scenesDirectory() / "Rock.usda", rockPlacement, false); !result) { return result; }
    if (auto result = LoadProp(scenesDirectory() / "Boat.usda", glm::mat4(1.0f), true); !result) { return result; }
```

It starts 25 m to the right of the rock and 30 m nearer the camera's start,
pointing away from the camera. At the top of `SeaObjects.cpp`, after
`ObjectReadback`:

```cpp
// Chapter 32 section 1: where the boat starts, and which way it points, in radians about +Y: 0 points its bow
// along -Z, as the camera starts. 25 m to the right of the rock and 30 m nearer the camera.
constexpr glm::vec4 BOAT_START{ 25.0f, 0.0f, -40.0f, 0.0f };
```

The panel can take the boat out of the sea (section 3 adds its checkbox), so
`SeaObjectSettings` gains, after `foamFade`:

```cpp
    bool  boat           = true;     // Chapter 32 section 1: the boat is in the sea
```

### Where the boat lives: on the GPU or the CPU

A boat floating on a sea is usually a CPU job: game code wants to know where
the boat is, and C++ is easier to write and to step through than a shader. The
boat here is moved on the GPU instead. Both work; they cost different things.

- **On the CPU**, the boat needs the water's height under its twelve points
  every frame. The water is three 256 × 256 FFTs made on the GPU this frame.
  The CPU can get it two ways. It can read the heights back (a small compute
  pass that samples the twelve points, then Chapter 20 section 9's readback),
  and they arrive a frame or two late: the boat floats on the sea of two frames
  ago, while the surface is drawn as it is now. At 60 frames a second that is
  33 ms and hardly shows; at 10 frames a second it is a fifth of a second, and
  the boat visibly sinks into crests and hangs over troughs. Or it can make the
  sea again on the CPU, which is three FFTs a frame, far too slow.
- **On the GPU**, one invocation moves the boat in the same command buffer,
  right after the maps are made, so the boat floats on exactly the water that
  is drawn. The cost is that now the *CPU* learns where the boat is a frame or
  two late, by the same readback. The camera that follows the boat and the panel
  can live with that (section 3). Game logic that must react to the boat at
  once could not.

This chapter picks the GPU: what you see is the boat on the sea you see, at any
frame rate. A game whose code needs the boat would take the first way, read the
heights back, and hide the lag; section 4 comes back to it. One invocation
leaves almost all of a GPU idle, which would be a waste for big work; the boat's
is small, four steps of twelve height lookups.

> **Jump:** until now, everything the GPU kept from frame to frame was a picture
> (a map, a cube) or a pile of particles that nobody needed one at a time. The
> boat is one object whose position *only the GPU* knows when it matters. Keep in
> mind from here that the CPU's idea of where the boat is, in the panel and for
> the camera, is always a frame or two behind, and that nothing on the CPU can
> push the boat directly: it can only pass the GPU settings, like the throttle.

### The boat's state

Where the boat is and how it moves stays on the GPU from frame to frame, in a
buffer the boat pass reads and writes. Its layout is a twin, in `SprayTypes.h`
after `SprayRequest`; section 2 says what each field is for:

```cpp
/* Chapter 32 section 1. The boat, as the GPU keeps it from frame to frame (std430, 144 bytes). */
struct BoatState
{
    mat4 model;                 /*   0: boat to world, for its vertex shader */
    vec4 position;              /*  64: xyz its middle, metres; w unused */
    vec4 orientation;           /*  80: a unit quaternion, xyz then w */
    vec4 velocity;              /*  96: xyz metres per second; w unused */
    vec4 angularVelocity;       /* 112: xyz radians per second, about world axes; w unused */
    vec4 status;                /* 128: x the hull's fraction under water; y speed, m/s; zw unused */
};
```

with its size checked beside the others,

```cpp
    static_assert(sizeof(BoatState) == 144, "BoatState layout drifted.");
```

and a flag that tells the passes the boat is in the sea, after
`SPRAY_FLAG_RESET`, whose comment now says what a reset does to the boat:

```cpp
#define SPRAY_FLAG_RESET 1u     /* put the boat back at its start, forget last frame's samples and foam */
#define SPRAY_FLAG_BOAT  2u     /* the boat is in the sea */
```

The buffer is a member beside Chapter 31's two,

```cpp
    vulkan_graphics::AllocatedBuffer m_boatState;   // BoatState (Chapter 32 section 1)
```

and `CreateBuffersAndImages` makes it after them and checks it with them, so
the function's first lines become:

```cpp
    // Three buffers the GPU keeps from frame to frame: what each sample point saw last frame
    // (section 5); the list of particles asked for, with its count in front (section 6); and the boat
    // (Chapter 32 section 1), which a copy also carries out to the CPU.
    m_probes    = createBuffer(m_context.vulkan, sizeof(glm::vec4) * SPRAY_SAMPLE_COUNT,
                               VK_BUFFER_USAGE_STORAGE_BUFFER_BIT, false);
    m_requests  = createBuffer(m_context.vulkan, 4 * sizeof(uint32_t) + sizeof(SprayRequest) * SPRAY_REQUEST_CAPACITY,
                               VK_BUFFER_USAGE_STORAGE_BUFFER_BIT | VK_BUFFER_USAGE_TRANSFER_DST_BIT, false);
    m_boatState = createBuffer(m_context.vulkan, sizeof(BoatState),
                               VK_BUFFER_USAGE_STORAGE_BUFFER_BIT | VK_BUFFER_USAGE_TRANSFER_SRC_BIT, false);
    if (m_probes.buffer == VK_NULL_HANDLE || m_requests.buffer == VK_NULL_HANDLE || m_boatState.buffer == VK_NULL_HANDLE)
```

It is a storage buffer, like the probes, and a transfer source as well, because
section 3 copies it out for the CPU. `Shutdown` destroys it beside the others:

```cpp
    destroyBuffer(m_context.vulkan, m_boatState);
```

**The probe set's binding 4.** Chapter 31 section 4 left binding 4 free for
this. The boat pass reads and writes the state there, the impact pass reads it
from section 3 on to place the boat's sample points, and the boat's vertex
shader reads it to draw the boat where the GPU put it (section 2). So it is the
one binding visible to the vertex stage as well. In `CreateProbeSet`, the
binding goes between 3 and 5,

```cpp
        { 4, VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,         1, compute | VK_SHADER_STAGE_VERTEX_BIT, nullptr },
```

the pool holds three storage buffers instead of two,

```cpp
        { VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,         3 },
```

and the writes become simpler. With the gap filled, the bindings run 0 to 6, so
a binding's number is its place in the table again, and the three buffers can
sit in one array in binding order. Replace the two buffer infos and the loop
with:

```cpp
    const VkDescriptorBufferInfo buffers[] = {
        { m_probes.buffer,    0, VK_WHOLE_SIZE },
        { m_boatState.buffer, 0, VK_WHOLE_SIZE },
        { m_requests.buffer,  0, VK_WHOLE_SIZE },
    };
    std::array<VkWriteDescriptorSet, std::size(bindings)> writes{};
    for (uint32_t binding = 0; binding < writes.size(); ++binding)
    {
        writes[binding] = VkWriteDescriptorSet{
            .sType           = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET,
            .dstSet          = m_probeSet,
            .dstBinding      = binding,
            .descriptorCount = 1,
            .descriptorType  = bindings[binding].descriptorType,
        };
        if (binding < 3)      { writes[binding].pImageInfo  = &images[binding]; }             // the maps
        else if (binding < 6) { writes[binding].pBufferInfo = &buffers[binding - 3]; }        // the buffers
        else                  { writes[binding].pImageInfo  = &images[SEA_CASCADE_COUNT]; }   // the foam
    }
```

### The boat pass

Section 2 writes the boat pass, `Shaders/Sea/SeaBoat.comp.glsl`, whole, once
the rigid body's pieces are in place. What it does with the columns is this
section's: for each of the twelve points under the hull, it turns the point
from the boat's own space into the world, asks Chapter 31 section 3's
`seaHeight` for the water above it, and takes the depth of the point under that
water, clamped to between 0 and the hull's 1.1 m; the column's push is
`ρ g A` times that depth, straight up, at the point. Everything else in the
pass turns twelve such pushes into one motion.

The pass's pipeline is the table of passes' third row, after the fade's,

```cpp
        { &m_boatPipeline,   "Sea/SeaBoat.comp.spv" },         // Chapter 32 section 1
```

with its member beside the other two compute pipelines, and destroyed with them:

```cpp
    VkPipeline            m_boatPipeline   = VK_NULL_HANDLE;   // Chapter 32
```

```cpp
    VkPipeline* pipelines[] = { &m_propPipeline, &m_boatPipeline, &m_fadePipeline, &m_impactPipeline };
```

It runs in `RecordSimulation` as step 3, the gap Chapter 31 left for it, after
the fade's dispatch and before the fade's barrier. The two touch nothing in
common, so the one barrier after both covers both:

```cpp
    // 3. Chapter 32 section 1: the boat moves. It touches nothing the fade does, so the two share the barrier.
    //    On the first frame it runs even with the boat out of the sea, to give its state numbers.
    if (m_settings.boat || m_reset)
    {
        vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_boatPipeline);
        vkCmdDispatch(commandBuffer, 1, 1, 1);
    }
    computeToComputeBarrier(commandBuffer);
```

It runs while the "Boat" setting is on. On the frame after a reset it runs
anyway, on or off, so that the boat's state holds a real boat, at rest at its
start, before anything reads it.

`PackSpray` passes the start and the flag. The start, after the weights,

```cpp
        .boatStart      = BOAT_START,
```

and the flag as the second half of the flags, which lose their comma:

```cpp
        .flags          = (m_reset ? SPRAY_FLAG_RESET : 0u)
                        | (m_settings.boat ? SPRAY_FLAG_BOAT : 0u),
```

## 2. One rigid body

### What the boat's state is

A rock does not move. A boat moves as one solid thing: a **rigid body**. Where
a rigid body is takes two things, its position and its orientation, and how it
moves takes two more, its velocity and its **angular velocity**, how fast it
turns and about which axis, as one arrow whose length is the turning speed in
radians per second. The GPU keeps all four from frame to frame in `BoatState`
(section 1), with two more things the pass writes for others: the boat's model
matrix, for its vertex shader, and its status, for the panel.

The orientation is a quaternion, Chapter 10 section 3's box that holds a
rotation. `rotationMatrix` turns it into a 3 × 3 rotation matrix, the formula
glm uses inside `glm::mat3_cast`, written out because GLSL has no quaternions.

### Force and torque

Every frame the columns push, gravity pulls, the water drags, and, from section
3, the engine drives. Each force does two things to a rigid body.

- **It moves it.** All the forces add up, wherever they act, and the sum
  divided by the mass is the acceleration: Newton's `a = F / m`, as for Chapter
  21's particles.
- **It turns it,** unless it acts through the centre of mass. How hard a force
  twists the body is its **torque**: the cross product of the arrow from the
  centre to where the force acts, *r*, and the force, *F*:

$$
\tau = r \times F
$$

The cross product is Chapter 10 section 8's: an arrow at right angles to both,
by the right-hand rule, as long as the push times the lever arm. Its direction
is the axis the force turns the body about. A worked example. A wave lifts the
bow so that the middle bow column, at `r = (0, −0.25, −2.2)` from the centre,
is 0.27 m deeper than the rest: an extra `F = (0, 3258, 0)` N. Then

$$
\tau = r \times F = (r_y F_z - r_z F_y,\; r_z F_x - r_x F_z,\; r_x F_y - r_y F_x) = (7168, 0, 0) \text{ N m}
$$

a twist about +X, the boat's sideways axis. By the right-hand rule that turns
−Z, the bow, upward: the bow rises, as it should.

How fast a torque turns the body depends on its **moment of inertia**, *I*, how
hard the body is to turn about that axis; the angular acceleration is `τ / I`,
as acceleration is `F / m`. A long boat is harder to turn end over end than
about its length. A solid box of mass *m* whose sides across the axis are *a*
and *b* has `I = m (a² + b²) / 12`: for 4000 kg the boat's size, 6.2 m long,
2.4 m wide, and 1.1 m deep, that is about 13,000 kg m² for pitching, 14,700 for
turning left and right, and 2300 for rolling. The boat's own numbers are close
to the box's — 12,400, 13,900, and 4000 — with roll raised, which gives a roll
that takes about two seconds back and forth, as a real boat of this size does.
The bow's 7168 N m pitches the boat at `7168 / 12,400 = 0.58` rad/s².

The three numbers are about the boat's own axes, which turn with it. So the
torque is turned into the boat's axes, divided by the three numbers, and the
answer turned back into the world's. A rotation matrix's **transpose** turns
the other way (its rows are its columns), which is what `transpose(rotation)`
does.

### Drag

Water resists anything moving through it, harder sideways than lengthways for a
hull: a keel slips forward and bites sideways, which is what keeps a boat
going where it points. Each column drags against its own point's velocity. A
point that is *r* from the centre of a body turning at ω moves at right angles
to both the axis and the arm, faster the further out it is: that velocity is
the cross product `ω × r`. Two metres from the centre of a boat yawing at
0.5 rad/s, a point moves at 1 m/s. So a column's velocity is the boat's
velocity plus `ω × r`, and its drag is in proportion to how wet it is and to
the direction in the boat's axes: full in x and y, a tenth along z, the boat's
length. Its torque comes with it, by the same cross product. Drag also calms
the boat: it takes energy out of every bob and roll, so the waves do not rock it
harder and harder.

### One step, and smaller steps

The step forward in time is Chapter 21 section 3's semi-implicit Euler, for
turning as for moving: the velocities first, from the accelerations, then the
position and orientation from the new velocities.

The orientation is a quaternion, and turning a quaternion by an angular
velocity ω for a short time *h* is

$$
q \leftarrow \operatorname{normalize}\!\left(q + \tfrac{h}{2}\,(\omega, 0)\,q\right)
$$

> **Jump:** this is the one formula in the chapter used without being derived.
> Hold on to two facts: `(ω, 0)` is ω written as a quaternion with a 0 in its
> fourth place — not a rotation, just four numbers — and the product with *q*
> is the quaternion product, `quaternionMultiply`. What the formula says is
> that a small turn by an angle θ about an axis is close to the quaternion
> `(axis × θ / 2, 1)`, and applying it to *q* adds that half-angle part times
> *q*. It is only close, which is why the result is normalized. Baraff's notes
> in Sources derive it.

A worked example. A boat at rest, `q = (0, 0, 0, 1)`, turning about +Y at
ω = 0.5 rad/s, for one step of *h* = 0.025 s:
`(h / 2) (ω, 0) q = 0.0125 × (0, 0.5, 0, 0) = (0, 0.00625, 0, 0)`, and the new
`q = (0, 0.00625, 0, 1)`, normalized `(0, 0.00625, 0, 0.99998)`. A quaternion
`(0, sin(θ/2), 0, cos(θ/2))` is a turn of θ about +Y, so θ = 2 × 0.00625 =
0.0125 rad, which is ω × *h*.

**Why four steps a frame.** The columns are springs: push the boat 1 cm down
and they push back with 1450 N more, 145,000 N per metre. A spring of stiffness
*k* holding a mass *m* bobs at `√(k / m)` radians per second, here
`√(145,000 / 4000)` ≈ 6 rad/s, about once a second. A step of semi-implicit
Euler stays stable only while the step is small next to that bob; past about a
third of a second per step, the boat gains energy each bob and flies off.
Chapter 09 section 7 caps a frame at 0.1 s, on a slow machine every frame is
that long, and a 0.1 s step is close enough to the edge to bob wrongly. Four
steps of 0.025 s each are well inside, and cost four times twelve height
lookups.

### The rock

The boat must not sail through the rock. After each step, if its centre is
closer to the rock's middle than the waterline plus 2.5 m, about half the boat,
it is put back on that circle, and whatever of its velocity points into the
rock is taken away. It is a wall, not a collision: no bounce, no spin. Enough
to keep the boat out.

### The whole pass

**This is `Shaders/Sea/SeaBoat.comp.glsl`, as section 2 has it**:

```glsl
// Shaders/Sea/SeaBoat.comp.glsl - one invocation moves the boat by one frame (Chapter 32): buoyancy
// at points under its hull (section 1), drag and a rigid body's motion (section 2), and the engine
// and the rudder (section 3). It runs on the GPU because the water it floats on is there.
#version 450
#extension GL_GOOGLE_include_directive : require
#include "SprayTypes.h"
#include "SeaWater.glsl"   // set 0, bindings 0-2: the sea's displacement maps

layout(local_size_x = 1) in;

layout(set = 0, binding = 4, std430) buffer BoatBuffer { BoatState boat; };

layout(push_constant) uniform PushConstants
{
    SprayParameters spray;
};

const float GRAVITY       = 9.81;      // m/s^2
const float WATER_DENSITY = 1025.0;    // kg/m^3, sea water
const float BOAT_MASS     = 4000.0;    // kg
const vec3  BOAT_INERTIA  = vec3(12400.0, 13900.0, 4000.0);   // kg m^2 about its own x (pitch), y (yaw), z (roll)
const float HULL_DEPTH    = 1.1;       // metres from the keel to the deck: no column is deeper
const float POINT_AREA    = 1.2;       // m^2 of hull bottom each point stands for
const float DRAG          = 3000.0;    // N per (m/s) per m^2 of fully submerged hull
const vec3  DRAG_SHAPE    = vec3(1.0, 1.0, 0.1);   // sideways, up and down, and lengthways: a hull slips forward
const int   SUBSTEPS      = 4;         // a frame cut into four steps keeps the stiff buoyancy stable

// Twelve points under the hull, in the boat's own space: bow along -Z, the keel at y = -0.25. The
// origin is the boat's centre of mass, low in the hull where the engine sits.
const vec3 HULL_POINTS[12] = vec3[](
    vec3(-0.5, -0.25, -2.2), vec3(0.0, -0.25, -2.2), vec3(0.5, -0.25, -2.2),
    vec3(-0.8, -0.25, -0.8), vec3(0.0, -0.25, -0.8), vec3(0.8, -0.25, -0.8),
    vec3(-0.8, -0.25,  0.6), vec3(0.0, -0.25,  0.6), vec3(0.8, -0.25,  0.6),
    vec3(-0.8, -0.25,  2.0), vec3(0.0, -0.25,  2.0), vec3(0.8, -0.25,  2.0));

// Section 2: a quaternion's rotation as a matrix (Chapter 10 section 3 used glm's).
mat3 rotationMatrix(vec4 q)
{
    float x = q.x, y = q.y, z = q.z, w = q.w;
    return mat3(1.0 - 2.0 * (y * y + z * z), 2.0 * (x * y + w * z),       2.0 * (x * z - w * y),
                2.0 * (x * y - w * z),       1.0 - 2.0 * (x * x + z * z), 2.0 * (y * z + w * x),
                2.0 * (x * z + w * y),       2.0 * (y * z - w * x),       1.0 - 2.0 * (x * x + y * y));
}

// The product of two quaternions: a turn by b, then by a.
vec4 quaternionMultiply(vec4 a, vec4 b)
{
    return vec4(a.w * b.xyz + b.w * a.xyz + cross(a.xyz, b.xyz), a.w * b.w - dot(a.xyz, b.xyz));
}

void main()
{
    if ((spray.flags & SPRAY_FLAG_RESET) != 0u)
    {
        // At its start, pointing along its heading, at rest.
        float heading        = spray.boatStart.w;
        boat.position        = vec4(spray.boatStart.xyz, 0.0);
        boat.orientation     = vec4(0.0, sin(0.5 * heading), 0.0, cos(0.5 * heading));
        boat.velocity        = vec4(0.0);
        boat.angularVelocity = vec4(0.0);
    }

    vec3  position        = boat.position.xyz;
    vec4  orientation     = boat.orientation;
    vec3  velocity        = boat.velocity.xyz;
    vec3  angularVelocity = boat.angularVelocity.xyz;
    float underwater      = 0.0;
    float h               = spray.deltaTime / float(SUBSTEPS);

    for (int substep = 0; substep < SUBSTEPS; ++substep)
    {
        mat3 rotation = rotationMatrix(orientation);
        vec3 force    = vec3(0.0, -BOAT_MASS * GRAVITY, 0.0);   // its weight, at its middle
        vec3 torque   = vec3(0.0);
        underwater    = 0.0;

        // 1. Buoyancy and drag at each point: Archimedes, a column at a time.
        for (int i = 0; i < 12; ++i)
        {
            vec3  offset = rotation * HULL_POINTS[i];   // from the middle to the point, in the world
            vec3  point  = position + offset;
            float depth  = clamp(seaHeight(point.xz, spray.patchSizes, spray.weights) - point.y, 0.0, HULL_DEPTH);
            float wet    = depth / HULL_DEPTH;

            // The weight of the water the column pushes aside, pushing back up.
            vec3 lift = vec3(0.0, WATER_DENSITY * GRAVITY * POINT_AREA * depth, 0.0);

            // Drag against the point's own motion, measured in the boat's axes and so easier to
            // push forward than sideways: that is what keeps a boat going where it points.
            vec3 pointVelocity = velocity + cross(angularVelocity, offset);
            vec3 localVelocity = transpose(rotation) * pointVelocity;
            vec3 drag          = -rotation * (DRAG * POINT_AREA * wet * DRAG_SHAPE * localVelocity);

            force      += lift + drag;
            torque     += cross(offset, lift + drag);
            underwater += wet / 12.0;
        }

        // 3. Section 2: semi-implicit Euler (Chapter 21 section 3), for turning as for moving. The
        //    inertia is the boat's own, so the torque goes into its axes and the answer comes back out.
        vec3 angularAcceleration = rotation * ((transpose(rotation) * torque) / BOAT_INERTIA);
        velocity        += force / BOAT_MASS * h;
        angularVelocity += angularAcceleration * h;
        position        += velocity * h;
        orientation      = normalize(orientation + 0.5 * h * quaternionMultiply(vec4(angularVelocity, 0.0), orientation));

        // 4. The rock: no closer than its waterline plus about half a boat, and no speed into it.
        vec2  fromRock = position.xz - vec2(SPRAY_ROCK_X, SPRAY_ROCK_Z);
        float reach    = SPRAY_ROCK_WATERLINE + 2.5;
        float distanceToRock = length(fromRock);
        if (distanceToRock < reach && distanceToRock > 1e-3)
        {
            vec2 away    = fromRock / distanceToRock;
            position.xz  = vec2(SPRAY_ROCK_X, SPRAY_ROCK_Z) + away * reach;
            velocity.xz -= away * min(dot(velocity.xz, away), 0.0);
        }
    }

    // What the boat's vertex shader and the spray read, this frame.
    mat3 rotation        = rotationMatrix(orientation);
    boat.model           = mat4(vec4(rotation[0], 0.0), vec4(rotation[1], 0.0), vec4(rotation[2], 0.0), vec4(position, 1.0));
    boat.position        = vec4(position, 0.0);
    boat.orientation     = orientation;
    boat.velocity        = vec4(velocity, 0.0);
    boat.angularVelocity = vec4(angularVelocity, 0.0);
    boat.status          = vec4(underwater, length(velocity.xz), 0.0, 0.0);
}
```

The reset puts the boat at its start, its heading turned into a quaternion
about +Y, at rest. The last lines write what other passes and shaders read: the
model matrix — the rotation in its first three columns and the position in its
fourth, Chapter 10 section 3's translation-times-rotation — the state for next
frame, and the status, how much of the hull is wet and how fast it moves.

### Where the centre of mass is

The boat's origin, and so the point the twelve columns are measured from, is
its centre of mass, 0.25 m above the keel. That height decides whether the boat
rights itself. When the boat rolls, the columns on the low side deepen and push
harder, the high side's less, and that twists it back upright. But the points are
below the centre, so as the boat rolls they also swing sideways, toward the high
side, and their push, now off to that side, twists the other way. The further
below the centre the points are, the further they swing. A hull is as stable as
its weight is low, which is why real boats carry their engine and ballast deep.
Try it: change the twelve points' y from −0.25 to −0.6, which puts the centre of
mass in the middle of the hull, steer the boat in a hard circle in Chapter 30's
default sea, and within a few turns it capsizes. Put them back.

### Drawing the boat where the GPU put it

The boat is drawn by Chapter 31 section 2's pipeline, as the rock is, with one
difference: the CPU never knows where the boat is in time to push its matrix,
so its vertex shader reads the matrix the boat pass wrote this frame. **This is
`Shaders/Sea/SeaProp.vert.glsl`, as it ends**:

```glsl
// Shaders/Sea/SeaProp.vert.glsl - the rock and the boat (section 2; Chapter 32 section 2). The rock
// is placed by the CPU; the boat by the GPU, whose boat pass wrote its matrix this frame.
#version 450
#extension GL_GOOGLE_include_directive : require
#include "FrameBlock.glsl"      // set 0: frame.viewProjection
#include "SprayTypes.h"

layout(location = 0) in vec3 inPosition;   // Chapter 11's vertex: all four are declared, two are used
layout(location = 1) in vec3 inNormal;
layout(location = 2) in vec2 inUv;
layout(location = 3) in vec4 inTangent;

// Set 1: the probe set. readonly, as Chapter 21's vertex shader had to be.
layout(set = 1, binding = 4, std430) readonly buffer BoatBuffer { BoatState boat; };

layout(push_constant) uniform PushConstants
{
    PropParameters prop;
};

layout(location = 0) out vec3 worldNormal;

void main()
{
    mat4 model  = prop.color.w > 0.5 ? boat.model * prop.model : prop.model;
    worldNormal = mat3(model) * inNormal;   // rotations and moves only, no scale: Chapter 11 section 13 not needed
    gl_Position = frame.viewProjection * model * vec4(inPosition, 1.0);
}
```

The one line that is not Chapter 31's picks the model matrix. A part whose
`color.w` is 1 is the boat's, and its matrix is the boat's state times the
part's own place on the boat; for the rock, `color.w` is 0 and the matrix is
the push constant's. The state is read at set 1, binding 4: the probe set,
which section 1 made visible to the vertex stage. `readonly`, as Chapter 21's
vertex shader had to be, because a vertex shader may not write storage buffers
unless a device feature allows it.

So the props' pipeline layout gains the probe set as set 1. In
`CreatePipelines`, its layouts become two:

```cpp
    // Section 2: the rock and the boat. Set 0 the camera; set 1 the probe set, for the boat's state (Chapter 32).
    const VkDescriptorSetLayout setLayouts[] = { m_sceneRenderer->FrameSetLayout(), m_probeSetLayout };
    const VkPushConstantRange   propRange{ VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT, 0,
                                           sizeof(PropParameters) };
    const VkPipelineLayoutCreateInfo propLayoutInfo{
        .sType                  = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
        .setLayoutCount         = 2,
        .pSetLayouts            = setLayouts,
```

**This is `RecordDraw`, as it ends.** It binds the probe set as set 1, marks the
boat's parts with `color.w` 1, and leaves the boat out when the "Boat" setting
is off:

```cpp
void SeaObjects::RecordDraw(VkCommandBuffer commandBuffer, uint32_t frameIndex, const SeaParameters& sea) const
{
    // Section 2: inside the scene pass. The probe set is bound too, for binding 4: the boat's state (Chapter 32).
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, m_propPipeline);
    m_sceneRenderer->BindFrameSet(commandBuffer, m_propLayout, frameIndex);
    vkCmdBindDescriptorSets(commandBuffer, VK_PIPELINE_BIND_POINT_GRAPHICS, m_propLayout, 1, 1, &m_probeSet, 0, nullptr);

    for (const PropPart& part : m_parts)
    {
        if (part.boat && !m_settings.boat) { continue; }   // Chapter 32 section 2: a boat out of the sea is not drawn
        const GpuMesh&        mesh    = m_meshes[part.mesh];
        const scene::Submesh& submesh = mesh.submeshes[part.submesh];
        const PropParameters  prop{
            .model         = part.model,
            .color         = glm::vec4(part.color, part.boat ? 1.0f : 0.0f),
            .sunDirection  = sea.sunDirection,
            .sunIrradiance = sea.sunIrradiance,
        };
        vkCmdPushConstants(commandBuffer, m_propLayout, VK_SHADER_STAGE_VERTEX_BIT | VK_SHADER_STAGE_FRAGMENT_BIT,
                           0, sizeof(prop), &prop);
        const VkDeviceSize offset = 0;
        vkCmdBindVertexBuffers(commandBuffer, 0, 1, &mesh.vertexBuffer.buffer, &offset);
        vkCmdBindIndexBuffer(commandBuffer, mesh.indexBuffer.buffer, 0, VK_INDEX_TYPE_UINT32);
        vkCmdDrawIndexed(commandBuffer, submesh.indexCount, 1, submesh.firstIndex, 0, 0);
    }
}
```

Binding a set does not read anything; only a shader's use does, so binding it
while the rock draws costs nothing.

That makes the boat's state a buffer a compute shader writes and a vertex
shader reads in the same frame, which needs a hand-over. It goes in
`RecordSimulation` step 6, after the local foam's:

```cpp
    //    Chapter 32 section 2: the boat's state to the boat's vertex shader and the readback copy.
    memoryBarrier(commandBuffer,
                  VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                  VK_PIPELINE_STAGE_2_VERTEX_SHADER_BIT | VK_PIPELINE_STAGE_2_COPY_BIT,
                  VK_ACCESS_2_SHADER_STORAGE_READ_BIT | VK_ACCESS_2_TRANSFER_READ_BIT);
```

Q1: the boat pass's `COMPUTE_SHADER` before the boat's `VERTEX_SHADER`, and
before the `COPY` that section 3 adds to carry the state out to the CPU. Q2:
storage writes, made visible to storage reads and a transfer read. Q3: a buffer
has no layout. Naming the copy now, before it exists, costs nothing, and the
barrier needs no change when it arrives.

This barrier is one that synchronization validation cannot prove: take
`VERTEX_SHADER` out of it and the layer stays quiet. That is not the layer
missing something. Chapter 21's end barrier, inside the spray's
`RecordSimulation`, runs after the boat pass and is a global memory barrier
from `COMPUTE_SHADER` to `DRAW_INDIRECT`, `VERTEX_SHADER`, and `COPY`: it covers
every compute write before it, the boat's state included. The boat's barrier is
kept anyway, so that the boat does not depend on what the spray happens to do;
its three questions are the argument for it.

## Checkpoint

Rerun `GenerateProjects.bat` (`SeaBoat.comp.glsl` is new), build, and run with
`--demo Sea`. Fly to the boat, 25 m to the right of the rock: from about
`(25, 3, −28)`, looking ahead. You can now see:

- **the boat**, floating with its bottom a little under the water, rising and
  falling and pitching as waves pass under it, and rolling when they pass at an
  angle;
- **nobody at the helm**: it stays near its start, nudged by the waves and held
  there by the drag. The keys do nothing yet, and its bow throws no spray;
- the rock and its spray and foam, as Chapter 31 left them.

---

# Part 2 — Under way (sections 3-4)

The boat floats; now it moves. Part 2 gives it an engine and a rudder on the
arrow keys, lets the hull throw Chapter 31's spray and leave a wake in its foam
map, and brings the boat's state back to the CPU for the panel and for a camera
that follows it.

## 3. Steering, spray at the bow, a wake, and a camera that follows

### The engine and the rudder

An outboard engine pushes the boat along its bow, while the propeller is in the
water. The push is "Throttle" times 6000 N, scaled down when less than a quarter
of the hull is wet, which happens when the boat leaps off a crest. Against the
lengthways drag the boat reaches about 5 m/s, ten knots, in calm water.

A rudder turns a boat only when water flows past it, so its twist is the
rudder's angle times the boat's forward speed: hard over at 5 m/s, 10,000 N m
about +Y, which turns the boat in a circle about 30 m across. Right rudder,
positive, turns the boat clockwise seen from above, a negative turn about +Y.
**These are step 2's lines** in the boat pass, after step 1's loop:

```glsl
        // 2. Section 3: the engine pushes along the bow while the stern is wet; the rudder turns the
        //    boat by how fast it moves through the water. Right rudder turns clockwise seen from above.
        vec3  forward      = rotation * vec3(0.0, 0.0, -1.0);
        float forwardSpeed = dot(velocity, forward);
        force  += forward * (THRUST * spray.throttle * min(underwater * 4.0, 1.0));
        torque += vec3(0.0, -RUDDER * spray.rudder * forwardSpeed, 0.0);
```

and its two constants, after `DRAG_SHAPE`:

```glsl
const float THRUST        = 6000.0;    // section 3: N at full throttle
const float RUDDER        = 2000.0;    // section 3: N m of turn per m/s of speed at full rudder
```

`PackSpray` passes them, after the frame time:

```cpp
        .throttle       = m_throttle,
        .rudder         = m_rudder,
```

### The keys

The arrow keys steer: up and down move the throttle while they are held, and it
stays where it is left; left and right put the rudder over, and it swings back
to the middle when let go, as a tiller does. Chapter 10's fly controller uses
W, A, S, D, Q, and E, so the arrows are free. **This is `HandleEvent`**, which
only remembers which arrows are down, as Chapter 10's controllers do:

```cpp
void SeaObjects::HandleEvent(const window::Event& event)
{
    // Chapter 32 section 3: which arrow keys are held. Repeats change nothing.
    if (!event.isKeyboard() || event.action == GLFW_REPEAT) { return; }
    uint32_t bit = 0;
    switch (event.code)
    {
        case GLFW_KEY_UP:    bit = KEY_AHEAD;     break;
        case GLFW_KEY_DOWN:  bit = KEY_ASTERN;    break;
        case GLFW_KEY_LEFT:  bit = KEY_PORT;      break;
        case GLFW_KEY_RIGHT: bit = KEY_STARBOARD; break;
        default:             return;
    }
    m_heldKeys = event.action == GLFW_PRESS ? (m_heldKeys | bit) : (m_heldKeys & ~bit);
}
```

and the bits it uses, at the top of the file, after `BOAT_START`:

```cpp
// Chapter 32 section 3: the arrow keys, as bits of m_heldKeys.
enum HeldKey : uint32_t
{
    KEY_AHEAD     = 1u << 0,
    KEY_ASTERN    = 1u << 1,
    KEY_PORT      = 1u << 2,
    KEY_STARBOARD = 1u << 3,
};
```

In `SeaObjects.h`, `HandleEvent` is declared beside `Update`, and `Update`
takes the frame's time, for the keys, and the camera and its controls, for the
camera that follows the boat:

```cpp
    // In SeaDemo::Update: the arrow keys and the camera that follows the boat (Chapter 32), and the panel.
    void HandleEvent(const window::Event& event);
    void Update(float deltaSeconds, scene::CameraControls& controls, scene::Transform& cameraTransform);
```

The header's includes gain the two that declare those types,

```cpp
#include "PillowFort/Scene/CameraControls.h"
#include "PillowFort/Scene/Transform.h"
```

and the CPU state gains the keys, the throttle, and the rudder, after
`m_frameNumber`:

```cpp
    uint32_t                    m_heldKeys    = 0;       // Chapter 32 section 3: which arrow keys are down
    float                       m_throttle    = 0.0f;    // Chapter 32 section 3: -0.5 astern .. 1 full ahead
    float                       m_rudder      = 0.0f;    // Chapter 32 section 3: -1 port (left) .. 1 starboard (right)
```

In `SeaObjects.cpp`, `Update` takes the same three parameters,

```cpp
void SeaObjects::Update(float deltaSeconds, scene::CameraControls& controls, scene::Transform& cameraTransform)
```

`Update` turns the held keys into the throttle and the rudder, at its top. The
throttle moves half its range a second. The rudder closes the gap to where the
keys want it at four times the gap per second, Chapter 21 section 3's
exponential again, so it gets most of the way over in a quarter of a second:

```cpp
    // Chapter 32 section 3: up and down move the throttle while held, and it stays where it was left; left
    // and right put the rudder over, a quarter of a second to swing across, and it comes back to the
    // middle when let go.
    const float ahead = ((m_heldKeys & KEY_AHEAD) ? 1.0f : 0.0f) - ((m_heldKeys & KEY_ASTERN) ? 1.0f : 0.0f);
    const float turn  = ((m_heldKeys & KEY_STARBOARD) ? 1.0f : 0.0f) - ((m_heldKeys & KEY_PORT) ? 1.0f : 0.0f);
    m_throttle = std::clamp(m_throttle + 0.5f * ahead * deltaSeconds, -0.5f, 1.0f);
    m_rudder  += (turn - m_rudder) * std::min(4.0f * deltaSeconds, 1.0f);
```

`SeaDemo::Update` hands it the frame's events, beside the camera's controls,

```cpp
        m_objects.HandleEvent(event);   // Chapter 32: the arrow keys steer the boat
```

and calls it with the frame's time, the controls, and the camera:

```cpp
    m_objects.Update(input.deltaSeconds, m_controls, m_cameraTransform);   // Chapters 31-32: its panel, and the camera
```

### The boat's own spray, and its wake

Chapter 31's impact pass already does what a hull needs: it measures how fast
the water comes at a point at the water's edge, and sprays and leaves foam
where that is fast. The boat gets 16 sample points after the rock's 96, round
its hull at its waterline, from the stern along one side to the bow and back
along the other, each with its own direction out. They are written in the
boat's own space and carried along by its state every frame. Two things are
different from the rock's points:

- **The point moves.** A bow driving down into a wave, or a hull rolling into
  the water, deepens the point's submersion as surely as a rising wave does, so
  Chapter 31 section 5's rise already measures the hull slamming into the
  water. The boat's own velocity at the point is kept, too: half of it goes into
  the spray it throws, so a moving boat throws its spray forward.
- **A moving hull churns the water** whether or not it throws spray: foam by
  its speed, 0.15 per metre per second, stamped every frame and left behind,
  where it fades into a wake.

`SprayTypes.h` counts them, in place of Chapter 31's sample count:

```cpp
/* Section 5. Where the sea is sampled for spray: points around the rock's waterline, then points
   along the boat's bow and sides (Chapter 32 section 3). One invocation each. */
#define SPRAY_ROCK_SAMPLES     96u
#define SPRAY_BOAT_SAMPLES     16u
#define SPRAY_SAMPLE_COUNT    (SPRAY_ROCK_SAMPLES + SPRAY_BOAT_SAMPLES)
```

The probe buffer and the dispatch are sized by `SPRAY_SAMPLE_COUNT`, so they
grow with it. **These are the boat's lines** in `SprayImpact.comp.glsl`. Its
state, at binding 4, beside the probes:

```glsl
layout(set = 0, binding = 4, std430) readonly buffer BoatBuffer { BoatState boat; };
```

the points, above `stampFoam`:

```glsl
// Chapter 32 section 3: points round the boat's hull where the water meets it at rest, in its own
// space: xy is the point's x and z, zw which way is out, in x and z.
const vec4 BOAT_POINTS[SPRAY_BOAT_SAMPLES] = vec4[](
    vec4(-0.51,  3.00, -0.00,  1.00), vec4( 0.35,  3.00, -0.00,  1.00),
    vec4( 0.94,  2.73,  1.00,  0.00), vec4( 0.94,  1.87,  1.00,  0.00),
    vec4( 0.94,  1.01,  1.00,  0.00), vec4( 0.94,  0.15,  1.00,  0.00),
    vec4( 0.88, -0.71,  1.00, -0.09), vec4( 0.80, -1.56,  1.00, -0.09),
    vec4( 0.35, -2.25,  0.72, -0.69), vec4(-0.24, -2.36, -0.72, -0.69),
    vec4(-0.79, -1.72, -1.00, -0.09), vec4(-0.86, -0.86, -1.00, -0.09),
    vec4(-0.94, -0.01, -1.00, -0.09), vec4(-0.94,  0.85, -1.00,  0.00),
    vec4(-0.94,  1.71, -1.00,  0.00), vec4(-0.94,  2.57, -1.00,  0.00));
const float BOAT_WATERLINE = 0.0;    // the boat's own y where the water meets it at rest
const float WAKE_FOAM      = 0.15;   // Chapter 32 section 3: foam a hull leaves per m/s of its speed
```

the points themselves, as step 1's `else`, after the rock's `if`. They are
placed even while the boat is out of the sea, from the state the frame after a
reset always gives it (section 1):

```glsl
    else
    {
        // Round the boat's hull, carried along by the boat (Chapter 32 section 3).
        vec4 local     = BOAT_POINTS[id - SPRAY_ROCK_SAMPLES];
        mat3 rotation  = mat3(boat.model);
        vec3 offset    = rotation * vec3(local.x, BOAT_WATERLINE, local.y);
        point          = boat.position.xyz + offset;
        outward        = normalize(rotation * vec3(local.z, 0.0, local.w));
        objectVelocity = boat.velocity.xyz + cross(boat.angularVelocity.xyz, offset);
    }
```

the return for a boat out of the sea, between steps 2 and 3. It throws nothing
and leaves no wake, but by then its points have stored this frame's water, so
the frame it comes back compares with the frame before. Returning at the top of
the `else`, before the store, would leave their slots holding the frame the boat
left the sea, or, if it has been out since the demo started, memory nothing ever
wrote: the frame it came back would read seconds of change, or garbage, as one
frame's, hit the 20 m/s cap, and throw a fountain of spray and a ring of foam
round the hull:

```glsl
    // Chapter 32 section 3: a boat out of the sea throws nothing. Its points have still updated their
    // probes above, so that the frame it comes back compares with the frame before, not the one it left.
    if (id >= SPRAY_ROCK_SAMPLES && (spray.flags & SPRAY_FLAG_BOAT) == 0u) { return; }
```

and the wake, in step 4, before the stamp:

```glsl
    if (id >= SPRAY_ROCK_SAMPLES)
    {
        // Chapter 32 section 3: and where a hull churns through the water, by its speed, whether or not it
        // throws spray. Left behind, that foam fades into a wake.
        foam = max(foam, WAKE_FOAM * length(objectVelocity.xz));
    }
```

`mat3(boat.model)` is the boat's rotation, the model matrix's first three
columns. `boat.position` is its centre; the point's velocity is the boat's plus
`ω × r`, as in the boat pass's drag (section 2). Only the boat's sample points
are carried along with it; the wake stays where it was stamped, in the local
foam map, so it is left behind on the water as the boat moves on. The map
covers 256 m round the rock, and outside it the boat leaves no wake.

### Where the boat is, for the CPU

Two CPU things need the boat: the panel shows its speed, and the camera can
follow it. Chapter 31's readback already carries the spray's counters to the
CPU every frame; the boat's state rides in the same buffer, as
`ObjectReadback`'s second half:

```cpp
// Section 4: what one readback buffer holds. The spray's counters, for the panel (section 6), and the
// boat, for the panel and the camera (Chapter 32 section 3).
struct ObjectReadback
{
    particles::ParticleCounters counters;
    BoatState                   boat;
};
```

`RecordSimulation`'s step 7 copies it out beside the counters: its region after
`counterRegion`, and its copy after the counters' copy. Section 2's hand-over
already named `COPY` for it.

```cpp
    const VkBufferCopy boatRegion{ .srcOffset = 0, .dstOffset = offsetof(ObjectReadback, boat), .size = sizeof(BoatState) };
    vkCmdCopyBuffer(commandBuffer, m_boatState.buffer, m_readback[frameIndex].buffer, 1, &boatRegion);
```

`ReadResults` keeps it, one or two frames after it was copied, after the
counters:

```cpp
        m_boat     = latest.boat;   // Chapter 32 section 3
        m_haveBoat = true;
```

in two members after `m_counters`, the second saying whether the first holds
anything yet,

```cpp
    BoatState                   m_boat{};                // Chapter 32 section 3: likewise
    bool                        m_haveBoat    = false;   // m_boat holds something read back
```

and `Shutdown` forgets it, at its end:

```cpp
    m_haveBoat = false;
```

### The camera that follows

"Follow the boat" switches Chapter 10's controls to the orbit controller and
makes the boat its target every frame. The orbit keeps working, so dragging the
mouse still swings the camera round the boat. The target is the boat's position
from the readback, one or two frames old, at a fixed height a metre above the
mean sea, not the boat's own: a camera that rose and fell with every wave the
boat rode would make the viewer seasick, and it would also make the boat look
still while the sea moved. **These are the last lines of `Update`**, after the
panel:

```cpp
    // Chapter 32 section 3: the camera orbits the boat where the last readback put it, at the mean sea level
    // plus a metre, so that it does not bob with every wave the boat rides.
    if (m_settings.followBoat && m_haveBoat)
    {
        controls.orbit.target       = glm::vec3(m_boat.position.x, 1.0f, m_boat.position.z);
        cameraTransform.translation = controls.orbit.target - cameraTransform.Forward() * controls.orbit.distance;
    }
```

The orbit controller places its camera only when the mouse moves it (Chapter 10
section 6), so `Update` places it itself, on the line from the target back
along the camera's own forward direction, at the orbit's distance.

**This is the panel's boat group**, after the foam's:

```cpp
        ImGui::SeparatorText("Boat (Chapter 32)");
        ImGui::Checkbox("Boat", &m_settings.boat);
        if (ImGui::Checkbox("Follow the boat", &m_settings.followBoat) && m_settings.followBoat)
        {
            controls.Select(scene::ControllerKind::Orbit, cameraTransform);   // keep looking the same way
            controls.orbit.distance = 20.0f;
        }
        ImGui::TextDisabled("Arrow keys: up, down the throttle;");
        ImGui::TextDisabled("left, right the rudder");
        ImGui::SliderFloat("Throttle", &m_throttle, -0.5f, 1.0f);
        ImGui::Text("Rudder %+.2f", m_rudder);
        if (m_haveBoat)
        {
            ImGui::Text("Speed %.1f m/s", m_boat.status.y);
            ImGui::Text("%.0f%% of the hull under water", 100.0f * m_boat.status.x);
        }
```

and its setting, after the "Boat" setting of section 1:

```cpp
    bool  followBoat     = false;    // Chapter 32 section 3: the camera orbits the boat
```

Ticking "Follow the boat" selects the orbit controller with Chapter 10's
`Select`, which starts it round a point in front of the camera so that the view
does not jump, and sets a distance of 20 m; the next frame's target is then the
boat. The "Rock and boat" window opens as a title bar, under "Sea preview"; a
click opens it.

## 4. The frame, and where to go from here

### The frame, in order

`SeaDemo::Record`, as it is now, with the boat's additions to Chapter 31's frame:

```text
 top            Chapter 30's timestamps read; SeaObjects::ReadResults               31 §6, 32 §3
 1-8            Chapter 30: return trips, waves, FFT, maps, foam, hand-overs         31 §4
 9              the sky's Update                                                     (Chapter 30)
 Chapter 31     SeaObjects::RecordSimulation:
                  1 return trips   2 local foam fades   3 the boat moves   barrier   31 §7, 32 §1-3
                  4 impact: probes, requests, foam stamps, the wake   barrier        31 §5-7, 32 §3
                  5 Chapter 21's begin, emit, simulate, end                          31 §6
                  6 hand-overs: local foam, boat state   7 readback: counters, boat  31 §6-7, 32 §2-3
 10             the scene pass: the sea (+ local foam), the rock and the boat,       31 §2, 32 §2
                the sky
 Chapter 31     SeaObjects::RecordSpray: Chapter 21's second scope                   31 §6
                the scene target back to the engine
```

### What it costs

The boat is one invocation doing four steps of twelve lookups, each reading
three maps four times (Chapter 31 section 3); its sixteen sample points add a
sixth to the impact pass. Chapter 30's panel times them inside "maps". Untick
"Boat" to see what the boat adds on your GPU.

### Where to go from here

- **A wake that follows the boat anywhere.** The local foam map stays round the
  rock. A second one, centred on the camera and scrolled as it moves, would
  carry the wake across the whole sea; the scrolling is the hard part, since
  the map's contents must move by whole texels and the edge that comes into view
  must start clean.
- **The wake as waves.** A boat makes waves, the V-shaped Kelvin wake, not only
  foam. They could be added to the displacement, locally, as the foam is.
- **A boat the game can steer.** For game code that needs the boat at once,
  move it on the CPU: a small pass samples the water at the hull points, its
  results are read back, and the boat is drawn where the CPU puts it, with the
  frame or two of lag hidden by reading the heights a little ahead.

## Checkpoint

Rerun `GenerateProjects.bat`, build, and run with `--demo Sea`. Open "Rock and
boat". You can now see:

- **the boat, to the right of the rock**, floating with its bottom a little
  under the water, rising and falling and pitching as waves pass under it;
- **the engine.** Hold Up for two seconds: the throttle reaches 1, and the panel's
  speed climbs toward 4 to 5 m/s. Hold Left or Right and it turns, more slowly
  the slower it goes; at rest the rudder does nothing;
- **spray at the bow** when it drops into a wave, thrown forward with the boat,
  and **a wake**: a trail of foam behind it, fading out over 50 m or so.
  Steer in a circle and the wake is a ring;
- **the camera that follows.** Tick "Follow the boat" and drag with the left
  mouse button to swing round it;
- **the rock as a wall.** Steer into it: the boat stops against it and slides
  round it.

---

## When it does not work

| Symptom | Cause |
| --- | --- |
| `Initialize` fails with a file not found | `Boat.usda` is missing from `Assets/Scenes/` beside the executable: run Chapter 31's `make_sea_props.py` in `Assets/Scenes/` and build again |
| The boat sinks out of sight, or leaps into the sky | The buoyancy and the weight are out of balance: with `BOAT_MASS` 4000 kg, `POINT_AREA` 1.2 m², and twelve points, the boat floats with its bottom 0.27 m deep. A boat that leaps and keeps leaping higher is a step too long: check `SUBSTEPS` (section 2) |
| The boat spins or drifts with no keys held | A sign in the torque: the cross product is `cross(offset, force)`, offset first. Swapped, every twist is backwards, and the boat turns away from upright instead of toward it |
| The boat rolls over | Its points are too far below its centre of mass (section 2): the boat's file and `HULL_POINTS` must agree that the keel is 0.25 m below the origin |
| The boat floats a hand's width above or below the water as drawn | The surface is drawn from a grid two metres across a cell, which smooths away Chapter 30's shortest waves, while the boat floats on the maps themselves. A few centimetres of difference is expected |
| The boat is drawn at the origin, or not at all | Its parts' `color.w` is not 1, or the props' layout lacks set 1 and the vertex shader reads nothing at binding 4 (section 2) |
| The arrow keys do nothing | `SeaDemo::Update` does not hand the events to `HandleEvent`, or an ImGui window has the keyboard: click on the scene first |
| The wake cut off in a straight line | The local foam map's edge, 128 m from the rock. Outside it, the border reads no foam (Chapter 31 section 7) |

## Exit check

- [ ] Run with `--demo Sea` and open "Rock and boat". Drive the boat: Up for two
      seconds, then Right. The speed in the panel reads 4 to 5 m/s, the boat
      circles, and seen from above (fly up 90 m and look down) its wake is a ring
      that fades from one end.
- [ ] Tick "Follow the boat" and watch it ride a few swells: it pitches up as a
      crest reaches its bow and down as the crest passes under.
- [ ] Untick "Boat": the boat, its spray, and its wake are gone. Tick it again:
      it is where it was, and it comes back without a burst of spray or a ring
      of foam.
- [ ] The same at 4x MSAA, after resizing the window, and after switching to
      Ocean and back, which starts the boat again at its start, at rest.
      Synchronization validation, with the shader-access setting on (Chapter 20
      section 5), is silent through all of it.
- [ ] **The positive controls.** Each weakens a barrier this chapter relies on
      and must be reported by synchronization validation, with the shader-access
      setting on. Build each change on its own, run a few frames, read the
      messages, and put the barrier back.
  - **The boat handed to the impact pass.** In `RecordSimulation`, delete the
    `computeToComputeBarrier` after step 3. Expect `SYNC-HAZARD-READ-AFTER-WRITE`
    at the impact pass's `vkCmdDispatch`, binding 4, the boat's state, and
    `SYNC-HAZARD-WRITE-AFTER-WRITE` on binding 6, the foam the fade just wrote.
  - **The maps handed to the boat pass.** In `SeaDemo::Record` step 8, take
    `VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT` out of the displacement's
    destination. Expect `SYNC-HAZARD-READ-AFTER-WRITE` at `vkCmdDispatch`, for
    set 0, bindings 0, 1, and 2: now the boat pass, the first compute reader of
    the maps, sampling them before the assemble pass's writes are visible.
  - The boat's own hand-over to its vertex shader has no control that fires,
    for the reason section 2 gives.

---

## Sources

- Archimedes' principle, in any physics text: the push on a floating body is the
  weight of the fluid it displaces.
- David Baraff, *Physically Based Modeling: Rigid Body Simulation*, SIGGRAPH
  2001 course notes. Force, torque, inertia in a body's own axes, and the
  quaternion's rate of change, derived.
- Jacques Kerner, *Water interaction model for boats in video games*,
  Gamasutra, 2015. Buoyancy and drag a piece of hull at a time, the method this
  chapter's columns simplify.

## Appendix A — Three functions, as they end

Reference: the three functions of `SeaObjects.cpp` that the boat changes in the
most places, whole. Chapter 31's Appendix A has its includes, `Initialize`, and
`CreatePipelines`. `Shutdown` is Chapter 31 section 1's with three additions:
Chapter 31 section 6's `m_spray.Shutdown();` first, this chapter's section 1's
`destroyBuffer(m_context.vulkan, m_boatState);` beside the other buffers, and
section 3's `m_haveBoat = false;` at its end.

```cpp
SprayParameters SeaObjects::PackSpray(const SeaParameters& sea) const
{
    return SprayParameters{
        .patchSizes     = sea.patchSizes,
        .weights        = sea.weights,
        .boatStart      = BOAT_START,
        .deltaTime      = sea.deltaTime,
        .throttle       = m_throttle,
        .rudder         = m_rudder,
        .sprayThreshold = m_settings.sprayThreshold,
        .sprayRate      = m_settings.sprayRate,
        .sprayLaunch    = m_settings.sprayLaunch,
        .foamStamp      = m_settings.foamStamp,
        .foamFade       = m_settings.foamFade,
        .frameNumber    = m_frameNumber,
        .flags          = (m_reset ? SPRAY_FLAG_RESET : 0u)
                        | (m_settings.boat ? SPRAY_FLAG_BOAT : 0u),
    };
}
```

```cpp
void SeaObjects::Update(float deltaSeconds, scene::CameraControls& controls, scene::Transform& cameraTransform)
{
    // Chapter 32 section 3: up and down move the throttle while held, and it stays where it was left; left
    // and right put the rudder over, a quarter of a second to swing across, and it comes back to the
    // middle when let go.
    const float ahead = ((m_heldKeys & KEY_AHEAD) ? 1.0f : 0.0f) - ((m_heldKeys & KEY_ASTERN) ? 1.0f : 0.0f);
    const float turn  = ((m_heldKeys & KEY_STARBOARD) ? 1.0f : 0.0f) - ((m_heldKeys & KEY_PORT) ? 1.0f : 0.0f);
    m_throttle = std::clamp(m_throttle + 0.5f * ahead * deltaSeconds, -0.5f, 1.0f);
    m_rudder  += (turn - m_rudder) * std::min(4.0f * deltaSeconds, 1.0f);

    ImGui::SetNextWindowPos(ImVec2(360.0f, 275.0f), ImGuiCond_FirstUseEver);   // under "Sea preview"
    ImGui::SetNextWindowCollapsed(true, ImGuiCond_FirstUseEver);              // a title bar until clicked
    debug_panels::stopNextWindowAtScreenBottom();                              // open, taller than the room left
    if (ImGui::Begin("Rock and boat"))
    {
        if (ImGui::Button("Start again"))
        {
            m_reset = true;
        }

        ImGui::SeparatorText("Spray (sections 5 and 6)");
        ImGui::SliderFloat("Threshold (m/s)", &m_settings.sprayThreshold, 0.0f, 5.0f);
        ImGui::SliderFloat("Rate", &m_settings.sprayRate, 0.0f, 1000.0f, "%.0f");
        ImGui::SliderFloat("Launch", &m_settings.sprayLaunch, 0.0f, 20.0f);
        ImGui::SliderFloat("Drag", &m_settings.sprayDrag, 0.0f, 4.0f);
        ImGui::SliderFloat("Size (m)", &m_settings.spraySize, 0.05f, 1.0f);
        ImGui::SliderFloat("Opacity", &m_settings.sprayOpacity, 0.0f, 1.0f);
        ImGui::ColorEdit3("Spray", &m_settings.sprayColor.x);
        ImGui::Text("%u particles alive", SprayParticles::CAPACITY - m_counters.deadCount);
        ImGui::Text("%u new this frame", m_counters.emitCount);

        ImGui::SeparatorText("Foam (section 7)");
        ImGui::SliderFloat("Foam per m/s", &m_settings.foamStamp, 0.0f, 2.0f);
        ImGui::SliderFloat("Local foam fade (s)", &m_settings.foamFade, 0.5f, 30.0f, "%.1f", ImGuiSliderFlags_Logarithmic);

        ImGui::SeparatorText("Boat (Chapter 32)");
        ImGui::Checkbox("Boat", &m_settings.boat);
        if (ImGui::Checkbox("Follow the boat", &m_settings.followBoat) && m_settings.followBoat)
        {
            controls.Select(scene::ControllerKind::Orbit, cameraTransform);   // keep looking the same way
            controls.orbit.distance = 20.0f;
        }
        ImGui::TextDisabled("Arrow keys: up, down the throttle;");
        ImGui::TextDisabled("left, right the rudder");
        ImGui::SliderFloat("Throttle", &m_throttle, -0.5f, 1.0f);
        ImGui::Text("Rudder %+.2f", m_rudder);
        if (m_haveBoat)
        {
            ImGui::Text("Speed %.1f m/s", m_boat.status.y);
            ImGui::Text("%.0f%% of the hull under water", 100.0f * m_boat.status.x);
        }
    }
    ImGui::End();

    // Chapter 32 section 3: the camera orbits the boat where the last readback put it, at the mean sea level
    // plus a metre, so that it does not bob with every wave the boat rides.
    if (m_settings.followBoat && m_haveBoat)
    {
        controls.orbit.target       = glm::vec3(m_boat.position.x, 1.0f, m_boat.position.z);
        cameraTransform.translation = controls.orbit.target - cameraTransform.Forward() * controls.orbit.distance;
    }
}
```

```cpp
void SeaObjects::RecordSimulation(VkCommandBuffer commandBuffer, uint32_t frameIndex, const SeaParameters& sea)
{
    const SprayParameters spray = PackSpray(sea);

    // 1. Return trips. Last frame's compute passes wrote every buffer here; its draws read the spray
    //    and the boat's state, and its copy read them out. Chapter 21's barrier, for all of them at
    //    once. The local foam stays in GENERAL; last frame's surface sampled it.
    memoryBarrier(commandBuffer,
                  VK_PIPELINE_STAGE_2_DRAW_INDIRECT_BIT | VK_PIPELINE_STAGE_2_VERTEX_SHADER_BIT
                      | VK_PIPELINE_STAGE_2_COPY_BIT | VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT,
                  VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                  VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT,
                  VK_ACCESS_2_SHADER_STORAGE_READ_BIT | VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);
    transitionImage(commandBuffer, m_localFoamImage,
                    VK_IMAGE_LAYOUT_GENERAL, VK_IMAGE_LAYOUT_GENERAL,
                    VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_NONE,
                    VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT,
                    VK_ACCESS_2_SHADER_STORAGE_READ_BIT | VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT);

    vkCmdBindDescriptorSets(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_probeLayout, 0, 1, &m_probeSet, 0, nullptr);
    vkCmdPushConstants(commandBuffer, m_probeLayout, VK_SHADER_STAGE_COMPUTE_BIT, 0, sizeof(spray), &spray);

    // 2. Section 7: last frame's local foam fades.
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_fadePipeline);
    vkCmdDispatch(commandBuffer, groupCount(SPRAY_FOAM_TEXELS, 8), groupCount(SPRAY_FOAM_TEXELS, 8), 1);

    // 3. Chapter 32 section 1: the boat moves. It touches nothing the fade does, so the two share the barrier.
    //    On the first frame it runs even with the boat out of the sea, to give its state numbers.
    if (m_settings.boat || m_reset)
    {
        vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_boatPipeline);
        vkCmdDispatch(commandBuffer, 1, 1, 1);
    }
    computeToComputeBarrier(commandBuffer);

    // 4. Section 5: where the water comes at the rock and the boat fast, spray is asked for and foam
    //    left. The spray's begin pass reads the requests next.
    vkCmdBindPipeline(commandBuffer, VK_PIPELINE_BIND_POINT_COMPUTE, m_impactPipeline);
    vkCmdDispatch(commandBuffer, groupCount(SPRAY_SAMPLE_COUNT, SPRAY_GROUP_SIZE), 1, 1);
    computeToComputeBarrier(commandBuffer);

    // 5. Section 6: Chapter 21's frame, its emission sized by the requests.
    m_spray.RecordSimulation(commandBuffer, sea.deltaTime, m_settings.sprayDrag, m_reset);

    // 6. Hand-overs. The local foam to the surface's fragment shader, still in GENERAL (section 7).
    transitionImage(commandBuffer, m_localFoamImage,
                    VK_IMAGE_LAYOUT_GENERAL, VK_IMAGE_LAYOUT_GENERAL,
                    VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                    VK_PIPELINE_STAGE_2_FRAGMENT_SHADER_BIT, VK_ACCESS_2_SHADER_SAMPLED_READ_BIT);
    //    Chapter 32 section 2: the boat's state to the boat's vertex shader and the readback copy.
    memoryBarrier(commandBuffer,
                  VK_PIPELINE_STAGE_2_COMPUTE_SHADER_BIT, VK_ACCESS_2_SHADER_STORAGE_WRITE_BIT,
                  VK_PIPELINE_STAGE_2_VERTEX_SHADER_BIT | VK_PIPELINE_STAGE_2_COPY_BIT,
                  VK_ACCESS_2_SHADER_STORAGE_READ_BIT | VK_ACCESS_2_TRANSFER_READ_BIT);

    // 7. Section 6: Chapter 20 section 9's readback, the spray's counters for the panel and, from
    //    Chapter 32 section 3, the boat.
    const VkBufferCopy counterRegion{ .srcOffset = 0, .dstOffset = offsetof(ObjectReadback, counters),
                                      .size = sizeof(particles::ParticleCounters) };
    const VkBufferCopy boatRegion{ .srcOffset = 0, .dstOffset = offsetof(ObjectReadback, boat), .size = sizeof(BoatState) };
    vkCmdCopyBuffer(commandBuffer, m_spray.CounterBuffer(), m_readback[frameIndex].buffer, 1, &counterRegion);
    vkCmdCopyBuffer(commandBuffer, m_boatState.buffer, m_readback[frameIndex].buffer, 1, &boatRegion);
    memoryBarrier(commandBuffer,
                  VK_PIPELINE_STAGE_2_COPY_BIT, VK_ACCESS_2_TRANSFER_WRITE_BIT,
                  VK_PIPELINE_STAGE_2_HOST_BIT, VK_ACCESS_2_HOST_READ_BIT);
    m_readbackPending[frameIndex] = true;

    m_reset = false;
    ++m_frameNumber;
}
```

Next: [33 — Path Tracing](33-Path-Tracing.md)
