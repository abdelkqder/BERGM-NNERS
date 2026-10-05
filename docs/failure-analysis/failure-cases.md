# Failure cases: current Phase 1

All results below are simulated. **Recovered** means the exercised simulation continues correctly; **degraded** means information/capability is limited; **unrecovered** means a requirement remains unsatisfied under that condition. Hardware behavior is not established.

| ID | Failure / condition | Detection and response | Evidence / limit |
|---|---|---|---|
| FC-01 | Writer fails away from entry | Configured failure stops it; beacon copies continue relaying and Executors use the preserved records | Recovered for preserved records: `jury_demo --scenario writer-failure`; undiscovered events remain unknown. Budget exhaustion is different: it initiates a return, not power loss. |
| FC-02 | Random radio loss | Missing hop ACK triggers retry/re-parenting and buffering | `tests/test_mesh_network.py`; moderate seeded loss can recover; total loss cannot. RF not measured. |
| FC-03 | Corrupt frame | CRC/decode rejection prevents forwarding | `tests/test_protocol.py`, `tests/test_gateway.py`, `tests/test_mesh_network.py`; CRC is corruption detection, not delivery. |
| FC-04 | Command Post unavailable | ONA buffers failed uplink callbacks and retries | `tests/test_gateway.py`, `tests/test_ona_mesh.py`; no durable restart buffer. |
| FC-05 | Unreachable target | Sense/replan, wait and retry per blockage policy, report BLOCKED/UNREACHABLE, return or hold per policy | `tests/test_executor_inherited.py`, `tests/test_phase1_system.py`; unresolved if no route or clearance capability exists. |
| FC-06 | Event absent at remembered position | Executor senses locally and writes CONTRADICTED through a beacon/ONA | `audit/verify_phase1.py`: contradiction record and executor events in supplemental JSON. No direct Executor-to-CP mutation. |
| FC-07 | No eligible record or capable executor | Planner makes no assignment; legacy empty-brief path also refuses a mission | `tests/test_phase1_system.py`, `tests/test_mission_dispatcher.py`; no automatic fallback search is claimed. Manual baseline search exists for comparison. |
| FC-08 | Repeated observation / replacement Writer alias | Writer suppresses redundant deployment; Living Map retains aliases and per-report version checks | `tests/test_writer.py`, `tests/test_phase1_repairs.py`; repeated copies do not add corroborations. |
| FC-09 | Incorrect GPS reference/heading | No calibration/detection mechanism | Unrecovered; coordinate tests prove mathematics only. Reference parameters are assumptions. |
| FC-10 | Known blocked passage | Hazard hints inform the Executor's discovered map and weighted replanning | `tests/test_executor_inherited.py`; alternative routes still depend on local sensing. |
| FC-11 | New debris after exploration | Executor detects discrepancy, replans and preserves BLOCKAGE observations | `simulation.dynamic_debris`, `tests/test_phase1_system.py`; degraded if no alternate path. |
| FC-12 | Debris seals target | First attempt blocks; Command Post dispatches DEBRIS, observes clearance, then retries original mission with a fresh attempt ID | `jury_demo --scenario debris-recovery`; requested clearance and target complete. Other blockages may remain navigation memory under on-demand policy. |
| FC-13 | Executor fault / low battery | Fault/battery states prevent redispatch; affected mission requeues once | `tests/test_phase1_system.py`, `tests/test_phase1_repairs.py`; modeled triggers, not measured failure rates. |
| FC-14 | Relay disappears | Parent expiry/ACK failure and buffering; restored connectivity delivers stored memory | `audit/verify_phase1.py`: existing four-hop test chain, relay disabled/restored; permanent partition remains degraded. |
| FC-15 | Odometry drift | Configurable noise exists; no SLAM/drift correction | Unrecovered; guided examples use ideal odometry. |
| FC-16 | Delayed/duplicate outcome after reassignment or retry | Attempt correlation closes only the corresponding assignment, outcomes are idempotent; newer fleet state remains intact | `tests/test_phase1_repairs.py`: previous assignment, retry, duplicate, legacy and sequence-wrap regressions. |
| FC-17 | Duplicate retry queue entry | Idempotent insertion by mission ID | `test_failure_requeues_one_copy`; guided completion checks queue uniqueness. |
| FC-18 | Outdated memory / moved host / alias clearance | Timestamp ordering, per-stream version checks, alias lookup and latest host update | `tests/test_phase1_repairs.py`; diagnostic history records incoming identity and version. |
| FC-19 | Identifier/version exhaustion | Range checks raise a clear error; no silent collision/wrap | `test_identity_and_version_exhaustion_is_explicit`; uint16 attempts also fail on exhaustion. There is no rollover protocol. |
| FC-20 | Guided demo finishes its last movement but final evidence is wrong | The controller checks every acceptance predicate before showing success. Conflicting saved copies and an extra retry produce a stopped demo with a readable reason. | `tests/test_jury_failures.py`; eleven injected failure cases and native rendered failure views in `audit/phase1/supplemental.json`. Missing instructions, health failures and missing returns time out as failures. Unexpected runtime errors are shown with diagnostics under Details. |

The supplied evidence includes age decay with unchanged lifecycle, Executor refresh, contradiction, relay reconnection, Writer failure and mission recovery. Native UI checks use scripted Pygame events; they are distinct from human manual testing.

Unaddressed physical limits include interference/collisions, calibration, true range and battery measurements, flash persistence and restarting the ONA/Command Post. Beacon battery depletion can be configured in the model, but its physical behavior is unmeasured. Robot PROGRAM acknowledgement approximates radio reception, not durable storage acceptance; full beacon storage can reject a record. Do not interpret these simulations as physical acceptance.
