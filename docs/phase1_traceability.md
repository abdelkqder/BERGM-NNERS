# Phase 1 traceability: challenge requirement -> implementation -> evidence

Labels used everywhere in this repository:

* **IMPLEMENTED** - the logic exists and is exercised by tests / a demo.
* **SIMULATED** - the behaviour is shown inside a model (world, radio, sensors, actuators). Not a hardware result.
* **PLANNED** - not built yet.
* **ASSUMED** - a parameter or hypothesis we chose; not measured.
* **MEASURED** - obtained from a physical experiment. **Nothing in this repository is MEASURED yet.**

`pytest -q` = the full suite (count in the README). Demo commands are in `docs/phase1_demo.md`.

| Challenge requirement | Implementation | Evidence | Status |
|---|---|---|---|
| Choose ONE environment | Mines / Tunnels: a GPS-denied maze of corridors (`simulation/scenario.py::BASE_GRID`) | any demo | SIMULATED |
| GPS-denied environment | Robots never read a global position: the Writer/Executor keep a dead-reckoned local pose (`common/pose.py`); the only GPS in the system is produced by the ONA | `tests/test_pose_and_frames.py`, `test_writer_beacon_coordinates_come_from_the_pose_not_the_map` | IMPLEMENTED / SIMULATED |
| Writer robot autonomy: autonomous exploration | Frontier exploration over the Writer's own discovered map; no stored route; seeded tie-breaks; return-to-entry without shutdown (`writer_robot/writer.py`, `navigation/engine.py`) | `simulation.writer_demo`; `test_phase1_system.py::test_writer_discovers_the_arena...`, `::test_different_seeds_give_different_trajectories`, `::test_environment_change_changes_the_writer_route` | IMPLEMENTED / SIMULATED |
| Detect at least 2 event types | FIRE and GAS (plus VICTIM_PRESENCE and BLOCKAGE in simulation) via `writer_robot/perception.py` (threshold detector on simulated readings) | `tests/test_perception.py`, `simulation.global_demo` | IMPLEMENTED / SIMULATED sensors. Real KY-026 / MQ-2 readings: PLANNED |
| Decide what to record | `writer_robot/memory_decision.py` (severity, confidence, redundancy) + `writer_robot/placement.py` (importance, host reuse, stock) | `tests/test_writer.py`, writer logs print the reason for every decision | IMPLEMENTED |
| Physical / simulated beacons + drop mechanism | `beacon/node.py` (memory + relay), `beacon/deployer.py` (finite stock; robot code only calls `drop()`) | `tests/test_mesh_network.py` | SIMULATED. Physical beacon + servo drop: PLANNED |
| Beacon message & signal design (what / where / when / version, ageing) | 18-byte `BeaconMessage` + `MeshFrame` envelope (`common/protocol.py`); confidence decay + staleness (`common/memory.py`) | `tests/test_protocol.py`, `test_living_map_lifecycle.py::test_age_and_confidence_follow_simulated_time...` | IMPLEMENTED. RF broadcast: SIMULATED. LoRa SX1278: PLANNED (transport is a stub) |
| Beacon network: multi-hop relay, TTL, duplicates, ACK/retry, buffering | gradient routing, hop-by-hop ACK + retry, TTL, `(origin, seq)` de-dup, store-and-forward (`beacon/node.py`, `communication/mesh.py`) | `tests/test_mesh_network.py`; global demo prints per-beacon hops (`--seed 5` gives a 7-hop chain) | IMPLEMENTED (logic) / SIMULATED (radio). Real RF range: NOT MEASURED |
| Frame translation: local -> GPS | `common/coordinates.py` (heading-aware), applied by the ONA (`gateway/ona_gateway.py::to_gps`) to every memory record and heartbeat | `tests/test_pose_and_frames.py` (origin, translation, heading, round trip, many poses), `tests/test_ona_mesh.py` | IMPLEMENTED (mathematics). **Real-world GPS accuracy: NOT MEASURED; no accuracy figure is claimed.** Reference point/heading are ASSUMED |
| Outside Network Area | `gateway/ona_gateway.py`: receive, validate (CRC, TTL, duplicates), translate, buffer, forward, mailbox. Never plans | `tests/test_ona_mesh.py`, `tests/test_architecture.py::test_ona_has_no_mission_planning_responsibility` | IMPLEMENTED / SIMULATED links. Wi-Fi/HTTP uplink and satellite: PLANNED |
| Disconnected zone | The radio medium blocks/attenuates by distance and walls; deep beacons cannot reach the ONA directly (`communication/mesh.py`) | `test_wall_attenuation_breaks_a_link...`, `test_out_of_range_nodes_cannot_hear_each_other` | SIMULATED |
| No direct robot <-> Command Post link | Robots hold a `RobotLink` (beacons + ONA only). Only the ONA holds callbacks into the Command Post. Enforced by import-boundary and wiring tests | `tests/test_architecture.py` (8 tests) | IMPLEMENTED (enforced in code) |
| Transfer to a distant command post | ONA -> Command Post callbacks (`on_memory`, `on_heartbeat`, `on_status`); briefs return through the ONA mailbox | `simulation.global_demo` section 7 | SIMULATED. Satellite / long-range link: PLANNED |
| Command Post live map | `command_post/map_state.py` (Living Map) + renderer panels (records, ONA detail, fleet, queue) | `tests/test_living_map_lifecycle.py`; `python run_simulation.py` | IMPLEMENTED |
| Mission priority / executor selection (Command Post is the planner) | `command_post/planner.py`: class weight x lifecycle status x live confidence x freshness - travel cost; specialist-first selection; structured, printed reasons | `tests/test_phase1_system.py::test_priority_...`, `::test_capability_matching...`; fleet demo decision table | IMPLEMENTED. Weights are ASSUMED |
| Executor robot: mission briefing | Brief composed by the Command Post (`build_brief`), carried by the ONA mailbox, polled by the Executor at the entry | `test_executor_gets_its_brief_only_through_the_ona_mailbox` | IMPLEMENTED / SIMULATED |
| Inherited memory / beacon-guided navigation | Brief = target + beacon waypoints + remembered blockages + blockage policy; weighted re-planning (`navigation/engine.py::plan_route`) | `tests/test_executor_inherited.py`, `simulation.compare_memory` | IMPLEMENTED / SIMULATED |
| Mission execution by capability | `executor_robot/capabilities.py` (FIRE, GAS, VICTIM, DEBRIS, GENERAL) + state machine | `tests/test_executor_inherited.py`, fleet demo | IMPLEMENTED / SIMULATED actuators |
| Executor updates the Living Map (feedback loop) | Executor writes its observation into a beacon (versioned); UNVERIFIED -> VERIFIED / ACTIVE / ESCALATED / CLEARED / CONTRADICTED | `test_executor_verifies_updates_memory_returns...` | IMPLEMENTED |
| Dynamic environment (debris after the Writer left) | `GroundTruthWorld.add_debris`, mutable `DiscoveredWorld`, discrepancy detection, BLOCKAGE memory, configurable `BlockagePolicy` | `simulation.dynamic_debris`; `tests/test_phase1_system.py` (7 tests) | IMPLEMENTED / SIMULATED |
| Continuity after Writer failure | `writer_fail_tick`, `force_fail()`; knowledge already in beacons reaches the Command Post | `test_writer_failure_leaves_the_knowledge_behind`; `global_demo --writer-fail` | SIMULATED |
| Executor return + next mission | RETURNING -> AVAILABLE; Command Post re-assigns | `test_a_mission_completes_and_the_executor_is_reassigned_a_new_one` | IMPLEMENTED |
| Failure cases | `docs/failure-analysis/failure-cases.md` (FC-01..FC-20) | tests named in that file; eleven deliberate stopped-demo cases | IMPLEMENTED (documented + simulated). Physical failure tests: PLANNED |
| GitHub repository | this checkout has an origin remote | `pytest -q`; reproducible commands in `docs/phase1_demo.md` | Repository present; latest local fixes remain uncommitted/unpublished in this work |
| Simulation demonstration | four seeded headless demos + comparison + pygame UI | `docs/phase1_demo.md` | IMPLEMENTED |
| Technical diagrams | `docs/architecture/system-architecture.md`, `docs/communication/beacon-protocol.md` | current flow, lifecycle and recovery diagrams | IMPLEMENTED |
| Implementation plan / physical prototype | `hardware/README.md`: stack, GPIOs, BOM, six-step validation sequence | Read the plan; physical execution remains separate | Plan DOCUMENTED, needs reconciliation; prototype PLANNED (Phase 2) |
| Real GPS accuracy, RF range, sensor calibration, battery life, drop mechanism | - | - | **NOT MEASURED / NOT BUILT** |

## Scored requirements: inspection index

Source: supplied challenge PDF, scoring on page 2. Its heading says **Initial Phase: 45 pts**, but the six listed deliverable categories total 25 and the seven technical categories total 35: **60 listed points**. We preserve the published weights; this table is coverage evidence, not a prediction or normalization of the jury score.

| Scored category | Points | Implementation / artifact | Reproduce and inspect | Remaining limitation |
|---|---:|---|---|---|
| GitHub repository | 4 | This checkout; README, requirements, tests | `python -m pytest -q`; [verification](../audit/phase1/verification.md) | Changes are local; publishing/submission is not part of this iteration |
| Simulation demo | 8 | Shared `JurySession`, existing Pygame renderer | [guided walkthrough](phase1_demo.md); [scenario evidence](../audit/phase1/scenarios.json); [captures](../audit/phase1/captures/) | SIMULATED world, sensing and actuators |
| Short technical report | 2 | [Six-page technical report](../output/pdf/phase1_technical_report.pdf) | Implementation status; beacon type/data; three vector diagrams; verified results; formal technical synthesis and physical/SLAM development plan. This supporting table retains the separate scored categories. All six pages rendered and inspected | Local artifact; publication/submission remains pending |
| Innovation, originality, creativity | 5 | Selective event/relay placement, inherited memory, aging and feedback | `python -m simulation.compare_memory --seeds 6`; [actual comparison](../audit/phase1/supplemental.json); inspect Writer decisions | Single modeled arena; no field-performance claims |
| Implementation plan | 3 | Approved repair/demo plan plus existing [hardware plan](../hardware/README.md) | [verification and remaining work](../audit/phase1/verification.md); hardware integration roadmap | Physical implementation and validation pending |
| Failure cases | 3 | [Failure analysis](failure-analysis/failure-cases.md), regressions, guided recovery | `python -B audit/verify_phase1.py`; Writer failure and debris scenarios | Some failures remain degraded/unrecovered, explicitly listed |
| Writer autonomy | 5 | `writer_robot/`, odometry, frontier policy, own discovered map | `python -m simulation.writer_demo --seed 42`; `tests/test_phase1_system.py`; guided Mission tab | Ideal odometry default; drift correction not implemented |
| Event detection and beacon deposition | 5 | FIRE/GAS detector, memory decision, placement, dispenser | Normal guided demo; `tests/test_perception.py`, `tests/test_writer.py`; Writer decisions in JSON | Sensors and drop mechanism SIMULATED |
| Beacon message and signal design | 5 | [Protocol layout](communication/beacon-protocol.md), CRC, mesh, decay | Memory tab: actual 39-byte frame; `tests/test_protocol.py`, `tests/test_mesh_network.py`; aging evidence | RF behavior and persistence unmeasured; finite capacities |
| Frame translation | 5 | `common/coordinates.py`, ONA conversion | Memory tab: local/GPS; `tests/test_pose_and_frames.py`, `tests/test_ona_mesh.py` | GPS reference and heading assumed; no physical accuracy claim |
| Outside Network Area | 5 | Validation, translation, buffering, mailbox; no planning | `tests/test_architecture.py`, `tests/test_ona_mesh.py`; packet/ONA counters in demos | Distant uplink is callback simulation, not satellite/Wi-Fi validation |
| Executor Robot | 5 | Inherited brief, capability actions, verification, updates, return | Three guided scenarios; `tests/test_executor_inherited.py`, `tests/test_jury_demo.py`; attempt correlation regressions | Robot motion and intervention SIMULATED |
| Technical solution diagrams | 5 | [Architecture, lifecycle, recovery sequence](architecture/system-architecture.md) | Follow diagrams alongside guided checkpoints and protocol table | Physical wiring details remain in hardware plan |

The general requirement for two physical robots remains part of the overall challenge. Simulated Writer/Executors satisfy the current simulation demonstration only; they are not proof of that physical requirement. Membership bonuses, registration and final-phase scoring are administrative/future items and are not claimed by code tests.
## What the tests do and do not prove

* A coordinate-transform test proves the mathematics (and the 7-decimal rounding of the output), **not** how well a real robot localises.
* Mesh tests prove the protocol logic against a simulated medium; they do not prove LoRa range, link budget or reliability.
* "Living Map vs baseline" numbers come from the simulator on one arena. They illustrate the effect of inherited memory; they are not field measurements.
