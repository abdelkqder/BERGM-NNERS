# Beacon and mesh protocol: current Phase 1

Implemented protocol logic over a **SIMULATED** radio. `common/protocol.py` is the format source of truth. The existing 18-byte beacon packet and MEMORY frame format are unchanged.

## What is beacon data?

Beacon data is the information a robot leaves about a finding so the next mission can use it: **what was found, where it is, when it was observed, and how reliable the report is**. A beacon is both a small record store and a radio relay. A relay-only beacon can have no findings; a storage beacon can have several (default capacity: four).

| Information | Field(s) in the implementation | Plain meaning |
|---|---|---|
| Host and event | `BeaconMessage.beacon_id`, `event_type` | Which radio marker stores the finding, and whether it concerns fire, gas or a blockage |
| Tunnel location | `x_local`, `y_local` | Position in metres in the entry's local coordinate frame; navigation derives direction/distance |
| Original observation | `timestamp`, `severity`, `initial_confidence` | Observation creation time, seriousness, and confidence supplied with the report |
| Finding identity/update | `MemoryExt.memory_id`, `version` | A logical finding ID and its incoming version; this is different from the host beacon ID |
| Latest observation | `last_update_ts`, `source` | When the information was last observed and which robot node reported it |
| Finding and passage state | `state`, `passage` | Whether the finding is unchecked/confirmed/still present/resolved/contradicted, and whether a passage is open/blocked |
| Packet health | `battery_pct`, CRC | Battery information and corruption detection |

The base packet and memory extension travel together. **GPS is not beacon packet data**: the ONA derives it after reception. Age, current confidence and staleness are computed from the latest observation time and clock; the packet does not carry a continuously changing age or freshness label. A record becoming old does not automatically mean a fire or blockage is cleared.

### Where the data lives and how it changes

1. The Writer detects a finding and writes it into a beacon using a PROGRAM message.
2. `BeaconNode.records` in [beacon/node.py](../../beacon/node.py) maps each memory ID to a pair: **`(BeaconMessage, MemoryExt)`**. Beacons relay MEMORY packets containing that pair toward the ONA.
3. The ONA validates and translates it. The Command Post creates a `MemoryRecord` in its Living Map with GPS, derived age/confidence, aliases and history. These outside-map fields are not all stored in the beacon packet.
4. The Command Post prepares a mission; the ONA delivers the brief. The Executor uses inherited locations/waypoints and its own sensing, then writes a new observation into a beacon.
5. The update follows the same beacon/ONA route back to the Living Map. Incoming report versions and observation timestamps prevent repeated or older copies undoing newer findings; the outside map's canonical revision can differ from a single incoming wire version after alias merges.

For example, the recorded seed-42 normal run ends with fire finding **258**, hosted by beacon **2**, at local **(2.0, -3.0) m**, updated to **CLEARED**. Its ONA-converted GPS is **(36.8064730, 10.1815225)**. The original report and later clearance refer to the same finding, rather than creating a second fire. See [scenario records and received packets](../../audit/phase1/scenarios.json).

### How to inspect it

In the guided demo, select **Findings**, click a record, and press **T** for Details. Scroll to see identity/version, host/source, age/confidence, local/GPS coordinates, history, and the actual received frame with byte count and relays. Packet bytes come from a bounded delivery trace; they are diagnostic evidence. A received frame is not a physical RF measurement.

The [technical report](../../output/pdf/phase1_technical_report.pdf) explains packet layout on page 2, section 4, and memory/ONA handling on page 3, sections 5-6.

**Storage limit:** all beacon and Living Map records currently reside in the running Python process. They survive a Writer failure while that process runs; they do not survive closing/restarting the application. JSON exports are diagnostic snapshots, not operational persistence. Database/restore logic and physical beacon flash storage are not implemented.

## Physical beacon packet

Little-endian layout, `struct` format `<BBffIBBB` plus CRC:

| Offset | Bytes | Field |
|---|---:|---|
| 0 | 1 | Host beacon ID |
| 1 | 1 | Event type ID |
| 2 | 4 | Local x, float32 metres |
| 6 | 4 | Local y, float32 metres |
| 10 | 4 | Observation creation timestamp, uint32 |
| 14 | 1 | Severity |
| 15 | 1 | Initial confidence |
| 16 | 1 | Battery percentage |
| 17 | 1 | CRC over preceding 17 bytes |

The implemented CRC is MSB-first, polynomial `0x31`, initial value zero, final XOR zero. Test vector `123456789` produces `0xA2`. Earlier documents called it MAXIM; that label was incorrect. The algorithm and on-wire bytes have not changed. CRC detects corruption; delivery depends on routing, acknowledgement and retry.

## Envelope and memory extension

```text
type(1) origin(1) seq(2) ttl(1) hops(1) link_src(1) link_dst(1) link_hops(1) len(1)
| payload | CRC(1)
```

The header is 10 bytes and the outer CRC is one byte. MEMORY adds the 10-byte extension `<HBBBIB` to the 18-byte beacon packet: memory ID (2), version (1), lifecycle (1), passage state (1), last observation timestamp (4), source node (1). Thus a MEMORY payload is 28 bytes and a complete MEMORY frame is **39 bytes**. GPS is added by the ONA and is not transmitted in this packet.

| Frame | Payload / responsibility |
|---|---|
| MEMORY | Beacon packet + memory extension; relay toward ONA |
| HEARTBEAT | Beacon position, gradient, parent, battery, record/version summaries |
| PROGRAM | Robot programs beacon position and optionally writes a record |
| STATUS | Executor state and mission outcome; carried to ONA |
| ACK | Origin and sequence of one acknowledged hop |
| HELLO | Probe; nearby nodes advertise their gradient |

## Assignment-safe STATUS compatibility

Legacy `<4sBBHB`: executor ID (4), state (1), battery (1), memory ID (2), outcome (1): **9 bytes**. Modern statuses append little-endian uint16 `attempt_id`: **11 bytes**, or **22 bytes including mesh header/CRC**. Attempt zero encodes the legacy form. Decoding accepts exactly 9 or 11 bytes and rejects other lengths.

The Command Post attaches a positive attempt ID to each new brief and retry. Executors echo it on state and outcome reports. Closing results must name the assigned target memory (aliases resolve canonically); BLOCKED can name its blockage memory. Late results cannot affect a newer assignment. Legacy zero-attempt reports cannot change modern assignments.

## Routing, aging and limits

- Node plan: ONA 0; beacons 1-63; Writers 64-79; Executors 128-191; broadcast 255. Memory IDs combine an 8-bit robot prefix and counter. Allocation/encoding checks reject exhausted identity/version ranges.
- `(origin, seq)` identifies packets; bounded seen sets suppress duplicates. Per-origin sequences intentionally wrap modulo 65536. TTL decreases and hop count increases per relay.
- Beacons learn gradients, acknowledge received hops, retry and buffer while disconnected. Records refresh periodically and survive a Writer failure in simulation.
- Robot `send_acked` approximates reception by the addressed radio endpoint; it does not prove durable record acceptance or physical RF reliability. Beacon storage and transport have finite capacities.
- Confidence decays from the latest observation using the simulation clock. Stale is a derived flag, separate from CLEARED/CONTRADICTED lifecycle.
- The Living Map tracks incoming versions per report ID and a canonical revision after alias merges. History/exports distinguish these. Version exhaustion is explicit; no rollover protocol is implemented.

Propagation, collisions, duty cycle, RF range, beacon flash persistence and real delivery guarantees remain unmeasured. Reproduce protocol tests with `python -m pytest -q tests/test_protocol.py tests/test_mesh_network.py tests/test_phase1_repairs.py`.
