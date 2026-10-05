# The Living Map: comprehensive project and delivered-code review

Review date: 5 October 2026. Reviewed source revision: `a7db087`.

This document records the project as delivered, the phase-one requirements in the supplied challenge PDF, the active software architecture, locally reproduced results, and the work that remains. It is an internal working summary, not the competition's six-page technical report. No application source was changed during this review.

## 1. Project purpose and current position

The Living Map addresses a specific continuity problem: a robot explores a disconnected, GPS-denied environment, learns something useful, and then leaves or fails. A later robot should be able to use that knowledge instead of rediscovering everything.

The proposed solution gives the environment a distributed memory through deposited radio beacons. A Writer explores and preserves selected observations; beacons store and relay them; an Outside Network Area (ONA) connects the disconnected zone to a Command Post; the Command Post assigns missions; an Executor enters with inherited information, verifies conditions, performs a simulated task, and updates the memory.

The repository chooses a mines/tunnels environment. FIRE and GAS are its core two hazard types. Victim-presence and debris capabilities extend the demonstration. Structural events exist in the type system but do not have a complete detector and executor implementation.

The delivered system is a substantial Python simulation proof of concept. It includes autonomous exploration, selective memory placement, a spatial beacon network, versioned event memory, mission planning, specialist executors, changing passages, and a feedback loop. The strongest demonstration is that knowledge remains useful after the Writer becomes unavailable and can be corrected when the environment changes.

It is not yet a physical robotics prototype. No firmware, physical radio driver, measured sensor behavior, real localization accuracy, or persistent storage across program restarts was established by the delivered code.

## 2. What phase one actually requires

Source: the supplied three-page document, **The Living Map: Spatial Memory for Emergency Robots**, IEEE RAS × IEEE AESS Tunisia Section Chapters, TSYP14. All three pages were text-extracted, rendered, and visually inspected. Its instructions were treated as project requirements to analyze, not permission to submit, contact organizers, or perform unrelated actions.

The brief lists these phase-one deliverables:

| Deliverable | Delivered material | Assessment |
|---|---|---|
| GitHub repository | Local Git repository, README, source, tests, license | Substantial material exists; remote submission/access was not checked |
| Simulation demonstration | Four principal demo modules, comparison, benchmark, Pygame UI | Headless demos reproduced; graphical operation not verified |
| Short technical report, maximum six pages | No finished report found in the delivered file inventory | Still needed, unless maintained elsewhere |
| Implementation plan | Hardware README, stack, GPIO plan, BOM, validation sequence | Useful foundation; needs reconciled quantities and a clearer execution schedule |
| Failure cases | `docs/failure-analysis/failure-cases.md`, FC-01 through FC-15 | Present, with some descriptions referring to older behavior |
| Technical solution and architecture | Architecture, protocol, and traceability documents | Present but internally inconsistent in places |

Technical coverage must include Writer autonomy, event detection and beacon deposition, beacon message/signal design, coordinate-frame translation, ONA architecture, Executor behavior, and system data flow.

The overall challenge requires at least two physical robots, a Writer and an Executor, and prohibits a direct robot-to-Command-Post link. Phase two explicitly requests the complete physical prototype. For phase one, explain how the simulation supports the eventual physical system without implying that hardware has already been built.

The PDF lists **5 October 2026** as the phase-one submission deadline and **1 December 2026** as the final deadline. Those are statements from the supplied document, not independently verified schedule updates.

There is an apparent scoring inconsistency: the PDF labels the initial phase as 45 points, but its six general items add to 25 and its seven technical items add to 35, totaling 60 if all are additive. Do not silently invent a corrected scoring scheme. The deliverable list itself is clear enough to organize the submission.

## 3. Architecture and ownership

```mermaid
flowchart LR
    W[Writer: explore and sense] -->|local PROGRAM| B[Beacon memory and relay network]
    B -->|MEMORY / HEARTBEAT / STATUS| O[ONA: validate, translate, buffer]
    O -->|simulated uplink callbacks| C[Command Post: map, priorities, fleet]
    C -->|mission brief| M[ONA mailbox at entry]
    M --> E[Executor: navigate, act, verify, return]
    E -->|memory updates and status| B
```

The Command Post makes mission decisions. The ONA carries information, converts coordinate frames, and buffers delivery; it does not choose missions. Robots use `RobotLink` and local beacon/ONA access rather than a Command Post handle. Architecture tests check imports, wiring, the absence of a Command Post radio node, and the inability of an isolated robot to report without a reachable uplink.

The actual simulation is one Python process. Radio transmission is modeled by queued byte frames. ONA-to-Command-Post delivery is a callback, and the mission downlink is a Python mailbox polled at the entry. These boundaries express the intended architecture, but they are not independent deployed services or physical wireless links.

### Repository map

| Area | Main responsibility and files |
|---|---|
| `common/` | Enums; observations; mission briefs; memory records; simulated clock; coordinate and pose models; packet serialization |
| `writer_robot/` | `writer.py` orchestrates exploration, sensing, preservation, bridging, and return; separate policies handle detection, memory selection, and placement |
| `beacon/` | `node.py` is the active multi-record mesh node; `deployer.py` supplies finite-stock dispensers and creates nodes; `memory_node.py` retains the older simple beacon |
| `communication/` | `mesh.py` supplies medium, ports, and robot links; `mock_transport.py` supports legacy/unit-test paths; `lora_transport.py` is a stub |
| `gateway/` | `ona_gateway.py`: validation, duplicate handling, local-to-GPS transform, buffering, heartbeat/status forwarding, brief mailbox |
| `command_post/` | `command_post.py` coordinates planning; `planner.py` ranks and selects; `mission_dispatcher.py` manages missions; `fleet.py` tracks availability; `map_state.py` owns the Living Map |
| `executor_robot/` | `executor.py` implements mission execution and updates; `capabilities.py` defines task profiles and fleet construction |
| `navigation/` | Shared A*, weighted route planning, frontier selection, and simulated movement |
| `simulation/` | Arena, scenario generation, wiring, metrics, demos, benchmark, renderer, and snapshots |
| `tests/` | Protocol, policies, navigation, integration, architecture, continuity, dynamic blockage, versioning, and fleet tests |
| `docs/`, `hardware/` | Demonstration instructions, requirement mapping, architecture, protocol, failure analysis, and physical implementation proposal |

`simulation/system.py::LiveMapSystem` is the main integration entry point. It constructs the world, radio medium, beacons, ONA, Command Post, and robots, then advances them on a shared clock. It supports concurrent actors and retains several backward-compatible entry points.

## 4. Three different kinds of map

Understanding this separation is essential:

1. **GroundTruthWorld:** the simulator's complete environment, including walls, hidden events, and debris. It provides sensor and actuator interfaces and evaluates outcomes.
2. **DiscoveredWorld:** an individual robot's accumulated local map. The Writer starts without the hidden layout; Executors also build their own discovered map.
3. **LivingMap:** the Command Post's collection of spatial event records and beacon health information received through the ONA.

The Living Map is principally semantic memory: what happened, where, how reliable the observation is, what state it is in, and what mission it should motivate. It is not a full SLAM reconstruction or a copied occupancy grid from the Writer.

An inherited mission contains a target, beacon-chain waypoints, remembered blockages, and a blockage policy. The Executor does not inherit every discovered cell. Simulator views may show arena geometry or evaluator information that the Command Post does not receive over the modeled network; presentations should label those views accordingly.

## 5. Writer behavior

The Writer combines several independent decisions:

- **Where to explore:** frontier selection over its discovered map, with information gain, distance, and risk terms. Seeded jitter can change route selection.
- **What is present:** synthetic readings pass through threshold detection and hysteresis. FIRE and GAS have implemented detection paths. Victim presence uses a sustained PIR-like signal.
- **What deserves memory:** `memory_decision.evaluate()` requires severity at least 2 and confidence at least 50%, and rejects nearby same-type observations already preserved by that Writer.
- **Where to store it:** reuse a suitable nearby beacon where possible; otherwise spend finite beacon stock on a new host. Low-stock rules favor more important events.
- **How to connect it:** when an event beacon lacks an uplink, the Writer can walk back toward a previously connected location and place bridge relays as needed.
- **How to finish:** return to the entry or become unavailable because of a configured failure/budget limit.

This is a rule-based autonomous policy, not a learned AI model. Its thresholds and utility weights are design assumptions.

`writer.dead` is a legacy completion predicate and can be true when the Writer has returned successfully. Use `writer.state` and `writer.returned` to distinguish RETURNED from DEAD when reporting results.

A replacement Writer begins with a blank discovered map. Existing beacon/Command Post knowledge can survive the earlier Writer; the replacement does not receive a hidden direct map handoff.

## 6. Beacon memory, radio, and reliability

The active `BeaconNode` stores multiple logical records, advertises heartbeat information, discovers an upstream parent, and forwards messages toward the ONA. Newer record versions replace older ones. Equal or older versions are ignored. When capacity is full, a closed record may be evicted; an all-open full store can reject another record.

The radio medium models range, wall attenuation, latency, and seeded random loss. It does not establish real LoRa range, collision behavior, duty-cycle compliance, antenna performance, or field reliability.

Protocol layers are distinct:

| Layer | Verified encoded size | Purpose |
|---|---:|---|
| Base `BeaconMessage` | 18 bytes | Host beacon ID, event type, local x/y, timestamp, severity, confidence, battery, CRC |
| Memory payload | 28 bytes | Base message plus logical memory ID, version, state, passage state, update time, and source |
| MEMORY mesh frame | 39 bytes | 10-byte relay header, 28-byte memory payload, and outer CRC |

Therefore, **18 bytes is not the complete active mesh MEMORY transmission**. PROGRAM, HEARTBEAT, STATUS, ACK, and HELLO have their own payloads.

The mesh includes hop counts, TTL, `(origin, sequence)` duplicate suppression, beacon ACK/retry, re-parenting, bounded buffering, and periodic record retransmission. CRC addresses corruption; it does not prove delivery.

One hardware-porting limitation is visible in `RadioPort.send_acked()`: it uses the simulated medium's recipient list as immediate evidence of receipt. Beacon relay nodes also implement explicit ACK frames, but robot-side programming does not wait for a real radio acknowledgment or confirm that storage accepted the record. Physical firmware needs a defined acceptance/acknowledgment contract.

The data is held in Python dictionaries and queues. It survives a simulated Writer failure because the beacon objects remain alive. It does not yet demonstrate survival of beacon power loss or a program restart.

## 7. Memory lifecycle and meaning

Logical records separate the identity of an event (`memory_id`) from the beacon hosting it (`host_beacon_id`). This supports several observations on one physical beacon and updates by later robots.

Records include event type, local/GPS position, severity, observation confidence, timestamps, source, version, lifecycle state, optional passage state, and history. Beacon health is tracked separately.

| State | Meaning |
|---|---|
| UNVERIFIED | Report exists but has not yet been confirmed by an Executor |
| VERIFIED | Executor confirms the observation |
| ACTIVE | Condition remains present following response |
| ESCALATED | Condition requires further action |
| CLEARED | Condition or obstruction is resolved |
| CONTRADICTED | Re-observation does not match the report |

These are possible outcomes, not a mandatory sequence traversed by every record. A run can move directly from UNVERIFIED to CLEARED.

Confidence decays exponentially from the latest observation, with rate `0.002` per simulated second and a floor of `0.05`. Staleness is a derived flag below `0.25`; it does not delete history or replace the lifecycle state. These constants are assumed, not calibrated from field observations.

The Command Post can merge nearby same-type open reports as corroboration. The current merge radius is 0.3 m. Identity reconciliation, concurrent updates, and version-counter wraparound deserve additional attention before longer-lived physical deployments.

## 8. Localization and coordinate conversion

Each robot maintains a local `(x, y, heading)` pose using an odometry model. Motion increments update the pose; optional Gaussian error is available, but default demonstrations use zero noise.

The frame convention is: origin at entry, local +x in the initial forward direction, local +y to the left. The global reference heading is counterclockwise from geographic east, not a compass bearing clockwise from north.

The ONA rotates local offsets into east/north offsets and uses an approximate flat-earth latitude/longitude conversion around a configured reference point. The default reference is `(36.8065, 10.1815)` with heading zero.

The simulator still uses discrete grid cells for navigation and sensing. Odometry is derived from simulated cell motion; the sensor model supplies relative event offsets. This is not measured encoder/IMU localization, SLAM, or physical event triangulation. Correct coordinate-transform tests establish arithmetic, not centimeter-level positioning accuracy. Errors in reference heading, reference GPS, odometry, and event localization all remain relevant to the physical design.

## 9. Command Post and Executor behavior

The Command Post ingests ONA data, maintains the Living Map, updates the mission queue, chooses available capabilities, and builds briefs. Priority combines severity, live confidence, freshness, event-class and lifecycle weights, a travel penalty, and a boost for blockages holding up another mission.

Victim, fire, gas, structural, and blockage classes have different weights. The travel penalty currently uses straight-line distance from the entry, not an estimated maze travel time. Executor selection favors specialists, then higher battery, fewer completed missions, and a stable ID tie-break. GENERAL covers FIRE and GAS verification only. A 35% battery threshold applies to dispatch eligibility.

The main Executor state sequence is:

`AVAILABLE -> ASSIGNED -> DEPLOYING -> ON_SITE -> WORKING -> VERIFYING -> UPDATE_MEMORY -> RETURNING -> AVAILABLE`

Additional branches handle waiting, failed missions, charging, repair, and out-of-service states.

Executors use weighted A* and can plan optimistically through unknown cells toward a known target. They sense, revise the discovered map, and re-plan when assumptions fail. A new obstruction can become a BLOCKAGE memory record, cause waiting/retry or return, and trigger a DEBRIS mission. Once cleared, the original mission can be re-queued.

Task effects are explicit simulator rules: FIRE can remove a fire; GAS reports ventilation but leaves gas present; VICTIM performs assessment while the victim remains; DEBRIS removes a blockage; GENERAL verifies without acting. Accordingly, completion of a mission does not necessarily mean elimination of the hazard.

The fleet demonstration uses ten available specialists by default. This is simulation scope, not evidence of ten physical robots. Scenarios without a fixed fleet can create executors on demand, another convenience that should not be presented as a resource-constrained physical deployment.

## 10. Validation reproduced during this review

Environment: Windows, Python 3.13.5, pytest 8.4.2. The project declares Python >=3.10, `pygame==2.6.1`, and pytest >=7.4. Tests and headless demos used the existing local Python installation.

### Automated tests

The normal documented command, `python -m pytest -q`, produced **362 passed, 1 failed in 107.67 seconds**.

The failing test was `tests/test_phase1_system.py::test_executor_contradicts_a_record_when_the_event_is_not_there`. It imports `tests.test_executor`, but this environment resolves `tests` to an unrelated package in Python's `site-packages`. The repository does not include a `tests/__init__.py` to establish its own regular package.

A targeted run using `--import-mode=importlib`, including `tests/test_executor.py` and the affected test, produced **5 passed**. The full suite with that mode then produced **363 passed in 82.00 seconds**. This identifies a test portability/import problem rather than a reproduced failure in contradiction handling. The full result is recorded in `audit/pytest-importlib.txt`; the default documented command still needs its import issue resolved.

### Seeded demonstrations

JSON results are saved under `audit/`.

| Run | Observed result |
|---|---|
| Writer, seed 42 | 100% reachable-cell coverage; 2/2 events found; 132 traveled cells; 66 m modeled odometry distance; 2 beacons; returned to entry |
| Global, seed 42 | 2 connected beacons; maximum 2 hops after Writer phase; FIRE became CLEARED, GAS became ACTIVE; both records advanced to version 2 |
| Fleet, seed 42 | Six assignments; E02 performed two missions; all ten fleet entries ended AVAILABLE |
| Dynamic debris, seed 42, `--placement seal` | Two new debris cells made the fire target unreachable; blockages were recorded; a Debris Executor cleared access; original mission completed on its second attempt |
| Writer failure, seed 42, tick 1500 | Headless failure scenario completed and preserved records remained available for executor updates |
| Global, seed 5 | Generated JSON shows 7 connected beacons and maximum 7 hops; the subsequent optional PNG export failed because Pygame is absent |

The Writer run's 264 simulated seconds are model time, not execution wall time. Frame-delivery counts can exceed transmitted-frame counts because one radio transmission may be received by several nodes; their ratio is not a delivery success percentage.

### Inherited-memory comparison

Command: `python -m simulation.compare_memory --seeds 6 --json`. Seeds 42 through 47 use the same arena and matched debris placement in both modes. The baseline is told which event class to find but receives no target position, beacon waypoints, or inherited hazards.

| Seed | Outbound cells, memory | Outbound cells, baseline | Mission ticks, memory | Mission ticks, baseline |
|---:|---:|---:|---:|---:|
| 42 | 36 | 74 | 938 | 1538 |
| 43 | 40 | 70 | 1268 | 1593 |
| 44 | 35 | 87 | 968 | 1783 |
| 45 | 31 | 31 | 998 | 1013 |
| 46 | 37 | 71 | 908 | 1447 |
| 47 | 19 | 19 | 638 | 647 |
| Mean | 33.0 | 58.7 | 953.0 | 1336.8 |

Both modes reached the target in all six runs. Mean outbound travel was approximately 43.8% lower with memory, and mean mission ticks approximately 28.7% lower. Two seeds showed equal outbound distance. These are small-sample simulation results on one arena, not universal performance gains or physical measurements.

The comparison establishes the benefit of the entire inherited-information brief relative to unaided search. It does not isolate the individual benefit of target coordinates, beacon waypoints, and hazard memory. Nor does it include the Writer's exploration/deployment cost in the Executor-only travel comparison.

### Graphical validation boundary

The Pygame renderer and snapshot exporter were inspected in source. Attempting PNG export raised `ModuleNotFoundError: No module named 'pygame'`. No interactive graphical session, screenshot, or manual UI acceptance is claimed. This is a missing local dependency, not evidence that the renderer itself is defective.

## 11. Important gaps and inconsistencies

1. **Submission packaging is incomplete in this checkout.** No finished six-page report or recorded demo was found. The code alone is not the whole phase-one deliverable set.
2. **Default test execution is not portable in the inspected environment.** Resolve the `tests` package collision and verify the ordinary documented command in an isolated environment.
3. **Architecture documentation mixes old and new flows.** Older diagrams still show direct Executor feedback callbacks, MockTransport as the system path, coordinates-only briefs, and return navigation as planned. The active mesh flow and implemented return behavior differ.
4. **Protocol text contradicts the active extension.** Earlier sections say lifecycle/version information never crosses the wire, while `MemoryExt` serializes it. The old event registry omits BLOCKAGE. Coordinate descriptions also sometimes equate local axes with east/north regardless of heading.
5. **Persistence terminology needs precision.** The current proof is survival of a robot failure within a running simulation, not nonvolatile storage or service-restart recovery.
6. **Simulation-to-hardware replacement requires more than a transport swap.** Robot code depends on simulated sensing, grid movement, radio-port conveniences, and actuator behavior. `LoRaTransport` raises `NotImplementedError`; physical sensing, navigation control, storage, and acknowledgment interfaces still need implementation.
7. **Perception claims need narrowing.** Executor on-site verification reads the sensed event type in `_target_present()` directly, rather than consistently passing through the threshold detector. Sensor snapshots expose localized events; physical flame/gas detection alone does not automatically provide those offsets. STRUCTURAL has an enum but no complete sensing/task path.
8. **Open hazards do not guarantee repeated missions.** ACTIVE/ESCALATED can close an individual mission while the record remains open. `CommandPost.on_memory()` deliberately avoids recreating finished/parked missions. A policy for sustained gas, escalation, human intervention, or follow-up dispatch remains important.
9. **Protocol boundaries deserve dedicated review.** Versions are encoded into one byte while ordering uses ordinary comparison; long-lived wraparound is not resolved. Robot-side receipt is not storage acceptance. CRC variant naming should be checked against an external interoperability vector before firmware is written; the current function returns `0xA2` for `123456789`.
10. **Hardware quantities need reconciliation.** The BOM says two robots, four beacons, and one ONA, but lists five ESP32 units despite Nano-based beacons; the purpose of the extra units is unclear. Its listed line totals do correctly sum to the displayed 675 TND. Supplier prices and electrical design were not verified.
11. **Physical beacon-stock assumptions are not aligned with demos.** Phase-one helper scenarios use 16 Writer beacons and a ten-executor fleet; seed 5 used seven beacons. The hardware proposal lists four. A four-beacon scenario should be part of feasibility validation if that inventory is retained.
12. **Repository hygiene needs work.** Generated Python bytecode is already tracked despite `.gitignore` excluding it. Running the code changes those tracked artifacts. Remove generated files from version control in a separate cleanup change while retaining source/tests.

Other known limits include ideal default odometry, a fixed base arena, assumed radio/sensor parameters, no measured battery model, simplified task effects, and no demonstrated physical collision avoidance between concurrent robots.

## 12. Recommended phase-one work order

### First: establish a reproducible baseline

Create a project virtual environment, install declared dependencies, fix the test import problem, verify the full normal test command, and run the Pygame UI. Capture exact commands and results. Clean tracked bytecode through an explicit repository change. Retain the existing working architecture while addressing specific defects.

### Second: make documentation match the delivered system

Replace historical architecture diagrams with one canonical current diagram. Separate base packet, memory extension, and mesh frame. Correct frame conventions and event lists. Describe the simulated ONA uplink and entry mailbox honestly. Reconcile implementation claims in the failure table, traceability file, README, and hardware plan.

### Third: package a focused demonstration

Use a short sequence showing Writer exploration, preservation, Writer unavailability, ONA translation, Executor inheritance, and a verified memory update. Add the sealed-debris scenario as evidence that memory can become wrong and be repaired. Seed 5 is useful for displaying a deeper relay chain; seed 42 is useful for a simpler narrative. Label simulation time and assumptions on screen.

### Fourth: produce the six-page submission report

A proposed page allocation, not an organizer-mandated template:

1. Problem, chosen environment, requirements, and proposed contribution.
2. Architecture, data flow, ONA boundary, and map separation.
3. Writer exploration, sensing, memory decisions, and beacon placement.
4. Packet design, relay reliability, memory lifecycle, and coordinate transform.
5. Executor planning, dynamic debris, reproduced results, and failure cases.
6. Implementation plan, reconciled hardware scope, limitations, and references/repository link.

Keep the submission centered on resilient spatial memory and mission continuity. The larger fleet is an extension; the essential physical target remains a Writer and an Executor.

### Fifth: prepare the physical transition

Define firmware-facing interfaces for sensing, motion, radio, nonvolatile memory, beacon deployment, and task effects. Reconcile BOM, quantities, power design, and beacon capacity. Then validate a single radio link, one programmable beacon, coordinate calibration, Writer deposition, ONA forwarding, and one Executor mission before expanding to multi-hop physical operation.

## 13. Commands and evidence locations

Run these from the `The-Living-Map-TSYP14` directory:

```powershell
python -m pytest -q
# Diagnostic workaround used in this review:
python -m pytest -q --import-mode=importlib

python -m simulation.global_demo --seed 42
python -m simulation.global_demo --seed 5
python -m simulation.global_demo --seed 42 --writer-fail 1500
python -m simulation.writer_demo --seed 42
python -m simulation.fleet_demo --seed 42
python -m simulation.dynamic_debris --seed 42 --placement seal
python -m simulation.compare_memory --seeds 6

# Requires the declared Pygame dependency:
python run_simulation.py --seed 42
```

Saved review evidence: `audit/global.json`, `audit/writer.json`, `audit/fleet.json`, `audit/debris.json`, `audit/failure.json`, `audit/comparison.json`, `audit/global-seed5.json`, `audit/targeted-tests.txt`, and `audit/pytest-importlib.txt`. The seed-5 JSON was emitted before optional PNG export failed; it must not be mistaken for successful image generation.

The main source-reading order for future work is: `simulation/system.py`, `writer_robot/writer.py`, `communication/mesh.py`, `beacon/node.py`, `gateway/ona_gateway.py`, `command_post/command_post.py`, `executor_robot/executor.py`, then the shared memory/protocol/navigation modules and their tests.

The project has enough working simulation behavior to build a credible phase-one submission. The immediate priorities are reproducibility, documentation consistency, graphical demonstration evidence, and the required report, followed by narrowly scoped improvements supported by tests.

## 14. Continued discovery: data model and storage

The follow-up investigation is documented in [Data model and storage discovery](docs/data-model-discovery.md). It maps every operational store, entity, identity, update path, capacity limit, and export boundary. There is no external database in the delivered application; operational state is held in Python objects.

A fresh seed-42 run confirmed that beacon records and the Command Post agreed on the final versions/states. Isolated additional probes reproduced consistency gaps not established by the earlier demos: alternate IDs from merged reports do not retain a canonical mapping, a clearance under an alternate ID can leave the canonical record open, a delayed previous-mission outcome can complete the current mission, and failed-mission re-queuing can duplicate the same queue object. One-byte versions and per-prefix memory counters also wrap, and brief exports omit operational fields.

Evidence and reproduction are saved in `audit/data-discovery.json` and `audit/discover_data.py`. These findings describe existing behavior; no fixes have been applied. They give us a more precise next-work order, beginning with record identity and mission-outcome correctness before expanding the system.
