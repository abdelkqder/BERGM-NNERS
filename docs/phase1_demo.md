# Phase 1 demonstration guide

## Guided inspection: three main demonstrations

Use the existing application with its guided controller. On Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -B run_simulation.py --guided --scenario normal --seed 42
```

The controller initially pauses. **Space / Continue** runs to the next checkpoint. **P** pauses/resumes; **R** restarts. Buttons or **1/2/3** choose normal response, explorer failure or blocked-route recovery. **Tab** switches Jobs/Findings; click a finding to inspect it. **T / Details** reveals technical evidence. Wheel/Up/Down scroll the data; the phase explanation stays visible. Default playback advances ten simulation ticks per display frame; `--speed 1` slows it down.

Every phase explains **Now** (what is happening), **Why** (why this step matters) and **Next** (what to wait for or do). In the code, the explorer is called the **Writer**, response robots are **Executors**, small radio markers are **beacons**, the entrance gateway is the **ONA**, and the outside command team is the **Command Post**.

1. **Normal:** the explorer saves fire and gas findings in radio markers, then returns. The entrance gateway passes those findings to the outside team and translates tunnel positions into GPS coordinates. The team sends suitable response robots. The fire is put out; the gas is checked and remains present. Both robots return ready for another job. Completing this demo does **not** mean the tunnel is safe.
2. **Explorer failure:** the explorer fails as planned at tick 1500, before returning. Its saved findings survive in the radio markers. Response robots still receive jobs, check the hazards, save new observations and return.
3. **Blocked-route recovery:** rubble is added after exploration. A fire response robot discovers that its route is blocked and reports the unfinished job. A rubble removal robot clears the requested obstruction. The original fire job retries once, with a different attempt number, and finishes. An unrelated obstruction can remain a saved finding awaiting a request; the demo does not claim it was cleared.

Jobs and Findings use everyday descriptions by default. Details exposes real states, mission/attempt IDs, preservation decisions, planning scores and actual selection reasons, plus memory versions, aliases, timestamps, confidence, source/host, local/GPS coordinates, relay details and actual received packet bytes. Radio connectivity lines do not imply walking paths.

Success requires expected observations, dispatched jobs finished, response robots ready at the entrance, no eligible work, and sixty further ticks of stable completion. All final acceptance checks must also pass, including agreement between saved copies and the outside map, and exactly one fire retry in the recovery demo. Missing results, timeouts and unexpected simulation errors stop with a readable reason. Space/P cannot resume a failed demo; R restarts it. Transport continues even when the older system phase reads complete.

The automated failure audit deliberately tests: exploration stopping before any saved finding, lost outside delivery, missing robot instructions, unavailable rubble removal, robot fault, low battery, a stranded robot, conflicting saved copies, an extra retry, a robot that never returns, and an unexpected runtime error. These eleven cases must stop with **failed** acceptance rather than show success. The expected explorer failure remains a successful recovery demonstration because its saved information supports the jobs.

## Reproduce the acceptance evidence

```powershell
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider --junitxml=audit/phase1/pytest.xml
.\.venv\Scripts\python.exe -B -m simulation.jury_demo --scenario all --seed 42 --output audit/phase1/scenarios.json --capture-dir audit/phase1/captures
.\.venv\Scripts\python.exe -B audit/verify_phase1.py --native
```

The first command uses normal pytest imports; `-B` avoids touching the repository's already-tracked bytecode. No `--import-mode` workaround is needed. The second runs the same controller headlessly, returns nonzero on failure, writes explanations/checks/decisions/packets and captures both tabs at each checkpoint. The third checks aging/refresh, contradiction by sensing, relay disconnect/buffer/reconnect, the deeper seed-5 chain, six comparison seeds, all eleven deliberate failures and scripted UI events (including Details) in a native Windows Pygame window. Omit `--native` for a dummy display in CI.

[Verification record](../audit/phase1/verification.md) separates pytest, headless scenarios, scripted native UI and visual inspection. Captures are Pygame-rendered frames; scripted UI acceptance is not a claim that a person manually completed the walkthrough. Attempt IDs are process-unique, so resets intentionally receive different IDs; trajectory and simulated-time behavior remain seeded.

The [six-page submission report](../output/pdf/phase1_technical_report.pdf) is now supplied. Publication/submission and physical hardware remain separate tasks.

## Existing demonstrations

The existing command-line demonstrations below are headless except the UI. Fresh processes with the same command and seed produce the same simulated behavior.
Numbers are produced by the simulation; **this guide does not quote performance figures** - run the commands.

```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m pytest -q                                     # the full suite
```

| # | Simulation | Command | What you should see |
|---|---|---|---|
| A | Global Living Map (main showcase) | `python -m simulation.global_demo --seed 42` | Writer map + route, beacon table with hops/parent, ONA table with local **and** GPS coordinates, Command Post decisions with reasons, executor timelines, Living Map before/after (UNVERIFIED -> CLEARED/ACTIVE) |
| A' | same, deeper chain | `python -m simulation.global_demo --seed 5` | a multi-hop beacon chain (several relays between the deepest beacon and the ONA) |
| A'' | Writer fails mid-exploration | `python -m simulation.global_demo --seed 42 --writer-fail 1500` | the Writer ends DEAD, not at the entry; what it already preserved still reaches the Command Post |
| B | Writer exploration / coverage | `python -m simulation.writer_demo --seed 42` | ASCII map of the discovered arena, coverage, distance, frontiers, dead ends, blocked paths, alternative routes, return success. `--debris 2` adds debris present at entry; `--compare 5` runs 5 seeds and counts distinct trajectories |
| C | Executor fleet + mission planning | `python -m simulation.fleet_demo --seed 42` | priority table with components, why each executor was chosen, mission history, executor timelines, memory updates, fleet status; one executor is re-assigned after returning. `--fault E02` breaks one executor: it ends NEEDS_REPAIR and gets no new mission |
| D | Dynamic debris | `python -m simulation.dynamic_debris --seed 42` | debris appears after the Writer left; Executor detects the discrepancy, re-plans, preserves the BLOCKAGE; Command Post updates the Living Map |
| D' | debris that seals the target | `python -m simulation.dynamic_debris --seed 42 --placement seal` | executor waits/retries, reports BLOCKED, Command Post dispatches a DEBRIS executor, memory becomes CLEARED, the original mission is re-queued and completes |
| D'' | other placements / policies | `--placement random`, `--placement chokepoint`, `--max-wait 20 --retries 0`, `--no-request-debris`, `--hold`, `--compare-seeds 6` | different seeds -> different debris cells and, potentially, different responses |
| E | With vs without inherited memory | `python -m simulation.compare_memory --seeds 6` | per-seed tables: travel distance, mission time, wrong turns, cells explored, replans, failed/repeated approaches, events recovered. Same arena, seed and debris in both modes; the Living-Map run does **not** know the new debris in advance |
| UI | Interactive pygame | `python run_simulation.py --seed 42` | keys: `W` writer, `E` executor, `X` drop debris, `D` replacement writer, `P` pause; click a record row to open its ONA detail |
| bench | Existing A/B/C benchmark | `python run_simulation.py --benchmark --seed 42 --difficulty MEDIUM` | unchanged from the previous revision, now over the beacon mesh |

Common options: `--seed N`, `--json` (machine-readable), `--png FILE` (headless snapshot with fog, routes, beacon links, debris, records).

Interpreting results honestly:

* A demo prints what happened in that run. If an effect is absent for some seeds (the comparison has seeds where memory gives no
  advantage because the target is near the entry), that is the result.
* The radio range, wall attenuation, task durations, priority weights and the GPS reference point are **assumptions** in code
  (see the traceability table). Nothing here is a hardware measurement.
