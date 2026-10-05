# Phase 1 verification record

**Scoped technical goal: PASS.** Generated 2026-10-05T16:36:44.806952+00:00.

Base commit `a7db087ff6c22c372f375f5b43971a02e8903e26` plus local uncommitted repairs and additions. Source fingerprint SHA-256: `89f068d991903aa5641c2733238fa5c24edd08d517311d1b96a86c113c7ed610`. [Machine record and per-file hashes](verification.json) identify the tested working tree; no new commit or remote publication is claimed. Earlier project/database discovery documents are historical pre-repair studies.

## Changes delivered

- Addressable memory aliases, per-report duplicate/version handling, observation-time ordering, canonical revisions and current host tracking.
- Positive dispatch-attempt IDs in briefs/statuses, late-outcome correlation, newer-state protection, idempotent outcomes and unique retry queue entries. Legacy nine-byte status compatibility remains; modern status adds two bytes.
- Explicit identity/version range errors, complete diagnostic exports and the local test-package import repair.
- One shared guided/headless controller, real completion predicates, Mission/Memory inspection tabs, bounded packet/Writer-decision diagnostics and full robot labels.
- Current architecture/protocol/failure documents and a [weighted scoring inspection index](../../docs/phase1_traceability.md).

## Plain-language and failure follow-up

Each phase now explains Now / Why / Next in a pinned panel. Jobs and Findings use everyday descriptions; Details preserves technical scoring evidence. Eleven deliberate failures stop with readable reasons and cannot resume via Space/P. The planned explorer failure still completes recovery. A discovered success-display gap is fixed: conflicting saved copies or an invalid retry count cannot show success. The timeout CLI was also verified to return exit code 1 and capture its stopped state. Seventeen targeted tests passed after the final display edits. Failure cases and native captures are recorded in supplemental JSON.

## Verification layers

| Layer | Result | Evidence |
|---|---|---|
| Regression-first reproduction | Initial new tests reproduced 12 failures before repairs | Tool execution history; existing pre-repair discovery evidence in `audit/` |
| Normal-import full suite | **399 passed; 0 failed/errors/skipped**, 100.080 s | [JUnit XML](pytest.xml) |
| Shared headless scenarios | All checks passed | [Scenario JSON: milestones, decisions, records, packets](scenarios.json) |
| Supplementary failure / continuity checks | All checks passed | [Age/refresh, contradiction, reconnect, deep chain, comparison](supplemental.json) |
| Scripted Pygame controls | Three scenarios; advance, pause, resume, reset, switch, select, scroll and Details toggle; native driver `windows` | [UI checks](supplemental.json), [rendered captures](ui/) |
| Actual CLI startup/shutdown | All three `--guided --scenario` entry points opened/returned normally on Windows | [CLI smoke record](cli-smoke.json) |
| Visual inspection | Full-size final Mission/Memory tabs and selected records, Writer-failure and debris checkpoints inspected; wrapping and scrolling accessible | [Inspected-file list](verification.json), [milestone captures](captures/) |

Scripted native UI checks and rendered-frame inspection are distinct from human manual interaction. 74 PNGs were generated; the machine record lists the representative full-size captures visually inspected. UI checks also verify text widths, button bounds and access to the final scrolled row.

| Main scenario | Acceptance | Final simulation tick |
|---|---|---:|
| normal | PASS | 3469 |
| writer-failure | PASS | 2329 |
| debris-recovery | PASS | 5249 |

Normal and Writer-failure missions finish with FIRE CLEARED and GAS ACTIVE after verification; Executors return AVAILABLE. Debris recovery uses two different FIRE dispatch attempts for the same target mission, with DEBRIS clearance between them. Under the existing on-demand policy, an unrelated BLOCKAGE can remain queued as navigation memory. Acceptance requires all dispatched work complete and no eligible missions, rather than claiming every blockage disappeared.

The relay diagnostic formed a four-hop chain, disabled its middle relay, retained the deepest beacon's record without delivery, restored the relay and observed the frame arriving. The existing seed-5 global run produced **7 hops**.

## Actual six-seed comparison

Model units: travel in cells; mission duration in simulation ticks. Both modes reached their targets in all twelve runs. No improvement threshold was imposed.

| Seed | Memory travel | Baseline travel | Memory mission ticks | Baseline mission ticks |
|---|---:|---:|---:|---:|
| 42 | 36 | 74 | 938 | 1538 |
| 43 | 40 | 70 | 1268 | 1593 |
| 44 | 35 | 87 | 968 | 1783 |
| 45 | 31 | 31 | 998 | 1013 |
| 46 | 37 | 71 | 908 | 1447 |
| 47 | 19 | 19 | 638 | 647 |

These are simulation results from one modeled arena, not field measurements.

## Reproduction

Run in the repository root with Python 3.13.5; this environment uses Pygame 2.6.1 and pytest 9.1.1 installed from `requirements.txt`.

```powershell
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider --junitxml=audit/phase1/pytest.xml
.\.venv\Scripts\python.exe -B -m simulation.jury_demo --scenario all --seed 42 --output audit/phase1/scenarios.json --capture-dir audit/phase1/captures
.\.venv\Scripts\python.exe -B audit/verify_phase1.py --native
```

Interactive walkthrough:

```powershell
.\.venv\Scripts\python.exe -B run_simulation.py --guided --scenario normal --seed 42
```

Use Space to advance, P to pause/resume, 1/2/3 to select scenarios, R to reset and Tab to switch views and T to toggle Details. The [demo guide](../../docs/phase1_demo.md) explains checkpoints and inspection fields.

## Remaining boundaries

The [six-page report](../../output/pdf/phase1_technical_report.pdf) was added in a subsequent documentation task, alongside Windows README instructions. [Report verification](report-verification.json) records its page count, hashes, visual inspection and command checks; the software test record above is unchanged.

The report was subsequently revised with simpler explanations, explicit implemented/planned status, the simulated beacon type and planned Arduino Nano/SX1278 hardware, a SLAM roadmap, and seven separate technical criteria with their published weights. Three vector diagrams show the finding/mission loop, actual 39-byte frame layout and blocked-route recovery. The final six pages were rebuilt, rendered at 125 dpi and visually inspected; text margins were checked. No runtime code changed and the full software suite was not rerun for these report edits.

Following presentation feedback, the report's last page was rewritten as a formal technical synthesis, physical integration/validation plan, SLAM development section and reproducibility note. The scoring checklist, rubric subtotal discussion and administrative submission comments were removed from that page; the weighted inspection index remains in `docs/phase1_traceability.md`. The revised report remains six pages. Its final page was visually rechecked, with unchanged preceding pages also verified.

Publication/submission, physical robots, RF/GPS/sensor calibration, real distant transport, SLAM and restart persistence remain outside the completed software/documentation work. All operational evidence is simulated. The PDF's initial-phase heading says 45 points while its listed categories total 60; weights are recorded without predicting a jury score.

Range exhaustion now raises errors; no rollover protocol exists. Radio reception acknowledgement does not prove durable beacon storage acceptance, and capacities remain finite. These limitations are documented rather than represented as fixed hardware behavior.
