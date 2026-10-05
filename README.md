# 🗺️ THE LIVING MAP

### Spatial Memory for Emergency Robots

**TSYP14 Technical Challenge — The Living Map**
**IEEE RAS × IEEE AESS Tunisia Section**

> **Give the environment a memory that survives the robot.**

## How to run from any project location

Use these instructions on **Windows, macOS or Linux**. Choose the desktop demo if you have a graphical desktop, or the headless runner for an SSH server, cloud machine or CI job. Windows/Python 3.13.5 is the platform tested here; macOS/Linux instructions follow the standard Python environment layout but have not been run on those operating systems in this workspace.

### 1. Get the project

Install [Python 3.13](https://www.python.org/downloads/) with pip. Git is optional if you download a ZIP. Internet access is needed to obtain dependencies during setup; the simulation itself runs locally and does not require robot hardware or a live network service.

With Git, clone into any folder you choose:

```text
git clone https://github.com/abdelkqder/BERGM-NNERS.git
cd The-Living-Map-TSYP14
```

Or use **GitHub -> Code -> Download ZIP**, extract it, and open a terminal inside the extracted folder containing **`run_simulation.py` and `requirements.txt`**. If you already have the project, use that folder directly. A shared local folder must include the latest source files; GitHub downloads contain only changes that have been published.

All commands below run **from that project folder**. They use relative paths, so the folder can be on your Desktop, Downloads, another drive or a remote machine. After moving/copying the source to a different location or computer, create a fresh `.venv` there; an old virtual environment is not portable. See [Python's venv documentation](https://docs.python.org/3.13/library/venv.html).

### 2A. Set up and launch on Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -B run_simulation.py --guided --scenario normal --seed 42
```

These commands use the virtual environment directly; activation is not required. If `python` is unavailable but the Windows Python launcher is installed, use `py -3.13 -m venv .venv` for the first command.

### 2B. Set up and launch on macOS or Linux (Terminal)

Check `python3 --version` first. If it selects a different Python version, use `python3.13` instead of `python3` when creating the environment.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -B run_simulation.py --guided --scenario normal --seed 42
```

Pygame 2.6.1, pinned in `requirements.txt`, publishes Python 3.13 packages for common Windows, macOS and Linux platforms. This package availability is separate from project acceptance testing. [Pygame release files](https://pypi.org/project/pygame/2.6.1/#files).

### 3. Use the guided window

The window starts paused. Press **Space** to run to the next phase. Each phase explains **Now / Why / Next**. Press **P** to pause/resume, **R** to restart, **Tab** to switch Jobs/Findings, and **T** to show technical details. Click a finding to inspect it; use the mouse wheel or Up/Down to scroll. **Q / Esc** closes the window. A stopped failure requires a restart.

Try the recovery demonstrations using **2 / 3** in the window, or launch them directly.

Windows:

```powershell
.\.venv\Scripts\python.exe -B run_simulation.py --guided --scenario writer-failure --seed 42
.\.venv\Scripts\python.exe -B run_simulation.py --guided --scenario debris-recovery --seed 42
```

macOS/Linux:

```bash
.venv/bin/python -B run_simulation.py --guided --scenario writer-failure --seed 42
.venv/bin/python -B run_simulation.py --guided --scenario debris-recovery --seed 42
```

The normal demo puts out the simulated fire and checks the gas; **the gas remains a hazard**. The failure demo proves saved findings survive the explorer. The debris demo clears a blocked route and retries the original fire job once. Add `--speed 1` to slow playback.

### 4. Run on a server, over SSH or in CI (no window)

Complete setup first, then run all three missions without a display. The runner prints **PASS/FAIL**, returns a nonzero exit code on failure, and writes a JSON result file. The output folder is created automatically.

Windows:

```powershell
.\.venv\Scripts\python.exe -B -m simulation.jury_demo --scenario all --seed 42 --output results/scenarios.json
.\.venv\Scripts\python.exe -B -m pytest -q
```

macOS/Linux:

```bash
.venv/bin/python -B -m simulation.jury_demo --scenario all --seed 42 --output results/scenarios.json
.venv/bin/python -B -m pytest -q
```

Expected result: PASS for `normal`, `writer-failure` and `debris-recovery`. The tests check software behavior separately from the three mission acceptance scenarios.

To also save screenshots without opening a window, add `--capture-dir results/captures` to the headless scenario command. Its capture mode selects Pygame's dummy display automatically unless you have already set `SDL_VIDEODRIVER`; a fresh terminal avoids overriding that default. Screenshots and JSON can be copied off a remote machine or collected as CI artifacts.

### 5. If startup fails

| Problem | What to do |
|---|---|
| `python` / `python3` is not found | Install Python 3.13; reopen the terminal. On Windows, try `py -3.13` for environment creation. |
| `run_simulation.py` or `requirements.txt` is not found | Change directory into the extracted/cloned project folder before running commands. Quote folder paths that contain spaces. |
| `No module named pygame` or `pytest` | Run the dependency-install command above using the same `.venv` interpreter used to launch the project. |
| Linux says `ensurepip` or `venv` is unavailable | Install your distribution's venv support package matching your Python interpreter, then recreate `.venv`. |
| No available video device / no desktop over SSH | Use the headless commands above. The guided window needs a graphical desktop session. |
| Installation attempts to compile Pygame or finds no matching package | Check the Python version/CPU architecture and consult the [Pygame installation guidance](https://pypi.org/project/pygame/2.6.1/); packages are not provided for every possible platform. |
| The folder was copied but `.venv` no longer works | Recreate the virtual environment in the new location and reinstall `requirements.txt`. |

To reproduce the full failure/continuity audit, use the [demonstration guide](docs/phase1_demo.md). All radio, sensing and robot intervention shown here are simulated.

[Six-page Phase 1 technical report (PDF)](output/pdf/phase1_technical_report.pdf)

---

## 🚨 The Challenge

Emergency robots operating inside **GPS-denied environments such as mines and tunnels** face a fundamental problem:

A robot may discover critical information — a fire, gas infiltration, victim, blocked passage — and then leave the area, lose communication, or fail.

When the next robot enters, should it have to start from zero?

**The Living Map explores a different approach: give the environment its own persistent spatial memory.**

---

## 💡 Our Approach

We are developing an **Adaptive Mission-Aware Spatial Memory** system in which information discovered by one robot can remain useful after that robot is gone.

Instead of keeping knowledge only inside a robot, the system preserves selected information in **distributed radio beacons** placed throughout the environment.

The information can then be:

**discovered → preserved → communicated → verified → updated → reused**

As the environment changes, the map changes with it.

---

## 🧠 System Architecture

```text
                 GPS-DENIED ENVIRONMENT
              ┌───────────────────────────┐
              │                           │
              │        WRITER ROBOT       │
              │      Explore & Sense      │
              │            │              │
              │            ▼              │
              │      BEACON NETWORK       │
              │      Spatial Memory       │
              │            │              │
              │      Multi-hop Relay      │
              │            │              │
              └────────────┼──────────────┘
                           ▼
                      ONA GATEWAY
                  Outside Network Area
                           │
                           │ Wi-Fi
                           ▼
                      COMMAND POST
                  Living Map & Planning
                           │
                           │ Mission Brief
                           ▼
                    EXECUTOR FLEET
             Fire • Gas • Victim • Debris
                           │
                           ▼
                  Memory Verification
                       & Update
                           │
                           └──────► Living Map
```

### Architectural Constraint

There is **no direct Robot ↔ Command Post communication**.

Information from the disconnected environment must pass through the **ONA and beacon communication network**.

---

## 🔄 The Living Map Loop

The system is built around a continuous information cycle:

```text
SENSE
  ↓
LOCALIZE
  ↓
UNDERSTAND
  ↓
PRESERVE CRITICAL INFORMATION
  ↓
STORE IN SPATIAL MEMORY
  ↓
COMMUNICATE THROUGH BEACONS
  ↓
COMMAND POST UPDATES THE LIVING MAP
  ↓
PRIORITIZE & ASSIGN A MISSION
  ↓
EXECUTOR USES INHERITED MEMORY
  ↓
VERIFY / DISCOVER CHANGES
  ↓
UPDATE THE MEMORY
  ↓
NEXT MISSION
```

The objective is not simply to record what a robot saw.

It is to preserve **what may still be useful for the next mission**.

---

## ✨ Key Concepts

### 🧭 Autonomous Exploration

The Writer explores a partially unknown environment using frontier-based exploration rather than following a fixed route.

It builds its own discovered map, handles obstacles and dead ends, and can return to the entry point.

### 📡 Spatial Memory & Multi-hop Communication

Beacons act as persistent memory nodes and communication relays.

Information from deeper parts of the tunnel can travel through neighboring beacons toward the ONA using a simulated multi-hop network.

### What data does a beacon store?

A beacon stores a **finding**, such as: "Fire was observed at this tunnel position, at this time, with this confidence." It can hold several findings; a beacon used only as a radio relay may hold none. The default simulated capacity is four findings per beacon.

| Saved data | What it tells the next mission |
|---|---|
| Event type and local x/y coordinates | What was found and where to go, in metres relative to the entry frame |
| Creation time and latest observation time | When it was first recorded and when it was last checked |
| Severity and observation confidence | How serious the event is and how reliable the observation was |
| Memory ID and version | Which finding this is and which update belongs to it |
| Finding state and passage state | Whether the hazard is unchecked, still present, cleared or contradicted; whether a passage is blocked/open |
| Host beacon ID and reporting robot | Which beacon holds the record and which robot supplied the observation |
| Battery and error-check bytes | Battery information and checks that detect corrupted packets |

**A beacon ID identifies the radio marker; a memory ID identifies a finding.** These are separate because one marker can store multiple findings.

The Writer saves a finding into a beacon. Beacons relay it to the entrance gateway (ONA), which adds GPS coordinates and forwards it to the outside Command Post. The Command Post uses it to prepare an Executor's mission. After checking the location, the Executor writes an updated observation back into a beacon. The radio record uses an **18-byte base packet plus a 10-byte memory extension**; the transmitted MEMORY frame is **39 bytes** including its envelope and error check. GPS, age and decayed confidence are added/calculated outside that compact packet; direction and travel distance are calculated from coordinates by navigation.

To inspect actual data, open **Findings**, select a record and press **T** for Details. It shows the record, host, update history and a received packet's bytes. [The beacon-data specification](docs/communication/beacon-protocol.md#what-is-beacon-data) explains the fields and storage locations; report pages 2-3 cover the packet and memory rules.

**Phase 1 storage is in memory:** saved findings survive a robot failure while the simulation continues, but disappear when the application closes. JSON exports are evidence, not a database or automatic restart recovery. Physical beacon flash storage remains planned.

### 🌍 Local → Global Coordinates

The Writer maintains a local pose `(x, y, θ)`.

The ONA transforms local coordinates into a global geographic reference used by the Command Post.

### 🧠 Adaptive Memory

Memory records contain information such as:

* event type
* local and global coordinates
* severity
* confidence
* timestamps and age
* source
* version
* verification status
* passage accessibility

Information can evolve from:

`UNVERIFIED → VERIFIED → ACTIVE → CLEARED`

or become:

`CONTRADICTED / ESCALATED`

### 🔀 Dynamic Environment

The environment is not assumed to remain static.

For example, debris may appear **after the Writer has already left**.

An Executor can discover the change, re-plan around it, preserve the new information, and update the Living Map.

### 🤖 Mission-Aware Executor Fleet

The Command Post matches missions with available executor capabilities:

| Executor  | Main mission                    |
| --------- | ------------------------------- |
| 🔥 FIRE   | Fire / thermal response         |
| 🧍 VICTIM | Victim investigation / response |
| ☁️ GAS    | Gas infiltration investigation  |
| 🧱 DEBRIS | Blockage / debris removal       |

Executors report their mission results and return to an operational state for future missions, or report failure/service requirements.

---

## 🎬 Phase 1 Simulations

The repository contains several complementary simulations rather than relying on one scenario.

### 1. Global Living Map

Demonstrates the complete system:

**Writer → Beacons → ONA → Command Post → Executor → Memory Update**

### 2. Writer Exploration

Focuses on:

* autonomous exploration
* map coverage
* dead ends
* obstacles
* alternative paths
* event discovery
* return to entry

### 3. Executor Fleet

Starts from an existing Living Map and demonstrates:

* priority analysis
* executor selection
* mission assignment
* navigation
* task execution
* memory verification
* return
* fleet availability

### 4. Dynamic Debris

Demonstrates a changing environment:

```text
Writer leaves
      ↓
New debris appears
      ↓
Executor encounters unexpected blockage
      ↓
Re-planning
      ↓
Blockage preserved in memory
      ↓
Debris Executor dispatched
      ↓
Obstacle cleared
      ↓
Original mission continues
```

### 5. Living Map Comparison

The project also includes a simulation comparison between:

**Executor without inherited memory**

and

**Executor using the Living Map**

using the same simulated environment to measure mission behavior.

---

## 🧪 Phase 1 Software Proof of Concept

This repository provides the **software and simulation foundation** for the project.

### Implemented / Simulated

* Autonomous Writer exploration
* Dynamic obstacle handling
* Persistent spatial memory
* Blockage memory
* Multi-hop beacon communication
* Packet validation and retry
* ONA gateway
* Local-to-global coordinate transformation
* Living Map
* Memory ageing and versioning
* Mission prioritization
* Capability-based executor assignment
* Specialized Executor state machines
* Executor feedback and memory updates
* Dynamic debris scenarios
* Writer failure / memory continuity
* Headless simulations
* Automated test suite

### Still Planned for the Physical Prototype

* ESP32 robot hardware
* physical LoRa communication
* physical beacon deployment
* real sensors and actuators
* real-world localization validation
* battery and sensor characterization

The simulations model these future physical interfaces but **do not claim physical measurements**.

---

## More commands (after setup)

Use the virtual environment created in the quick start above. The commands below show Windows syntax; on macOS/Linux replace `.\.venv\Scripts\python.exe` with `.venv/bin/python`.

### Existing headless demonstrations

```powershell
.\.venv\Scripts\python.exe -B -m simulation.global_demo --seed 42

.\.venv\Scripts\python.exe -B -m simulation.writer_demo --seed 42

.\.venv\Scripts\python.exe -B -m simulation.fleet_demo --seed 42

.\.venv\Scripts\python.exe -B -m simulation.dynamic_debris --seed 42

.\.venv\Scripts\python.exe -B -m simulation.compare_memory --seeds 6
```

Interactive Pygame simulation:

```powershell
.\.venv\Scripts\python.exe -B run_simulation.py --seed 42
```

---

## 📊 Repository Structure

```text
common/           Protocols, memory, coordinates, poses, missions
communication/    Simulated mesh / transport interfaces
beacon/           Memory nodes, relay, deployment
gateway/          ONA gateway
writer_robot/     Exploration, perception, memory decisions
executor_robot/   Executor capabilities and state machine
command_post/     Living Map, planning, fleet management
navigation/       A* and frontier exploration
simulation/       World, scenarios, demos and visualization
tests/            Automated tests
docs/             Architecture, protocol, failure analysis
```

---

## 📚 Documentation

[Phase 1 technical report (six-page PDF)](output/pdf/phase1_technical_report.pdf)

[Phase 1 verification and evidence](audit/phase1/verification.md)

📘 [Phase 1 Demonstration Guide](docs/phase1_demo.md)

📋 [Phase 1 Requirement Traceability](docs/phase1_traceability.md)

🏗️ [System Architecture](docs/architecture/system-architecture.md)

📡 [Communication Protocol](docs/communication/beacon-protocol.md)

⚠️ [Failure Cases](docs/failure-analysis/failure-cases.md)

---

## 🎯 Project Vision

The long-term vision is to evolve this first-generation demonstrator into a more capable emergency-robotics system with improved localization, communication, sensing, autonomous navigation and physical robustness.

The architecture is designed so that better hardware can replace simulated components without changing the fundamental system concept:

```text
Simulation
    ↓
Technology Demonstrator
    ↓
Physical Prototype
    ↓
Advanced Multi-Robot System
```

---

## 📌 Current Status

**Phase 1 — Software / Simulation Proof of Concept**

The repository is under active development as the project progresses toward the physical prototype.

---

### Core Idea

> **When the robot is gone, the knowledge should remain.**
