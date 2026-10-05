"""Read-only data-model discovery and isolated behavior probes.

Run from the repository root: python -B -X utf8 audit/discover_data.py
This creates fresh simulation objects and prints evidence as JSON.
"""
from __future__ import annotations

import json
import pathlib
import sys
from dataclasses import fields

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from beacon.node import BeaconNode
from command_post.fleet import FleetEntry
from command_post.map_state import BeaconHealth, LivingMap
from command_post.mission_dispatcher import MissionDispatcher, MissionRecord
from common.clock import SimClock
from common.enums import MemoryState, PassageState
from common.memory import MemoryRecord
from common.mission import BlockagePolicy, HazardHint, Mission, MissionTarget
from common.protocol import (
    BeaconMessage, ExecStatus, MemoryExt, MissionOutcome, ProgramCommand, decode_memory_payload,
    encode_memory_payload, memory_id_for,
)
from communication.mesh import RadioMedium, RadioPort
from gateway.ona_gateway import ONAGateway, UplinkStatus


def message(host=1, x=1.0, confidence=80):
    return BeaconMessage(host, "GAS", x, 0.0, 1_790_000_000, 2, confidence, 100)


def extension(mid=257, version=1, state=MemoryState.UNVERIFIED):
    return MemoryExt(mid, version, state, None, 1_790_000_000, 65)


def node(capacity=4):
    clock = SimClock()
    medium = RadioMedium()
    return BeaconNode(1, RadioPort(medium, 1, lambda: (1, 1), kind="beacon"),
                      clock.timestamp, capacity=capacity)


def probes():
    result = {}

    lm = LivingMap()
    canonical = lm.ingest(message(), extension())
    for _ in range(3):
        lm.ingest(message(host=2), extension(mid=513))
    result["repeated_merged_report"] = {
        "stored_records": len(lm), "canonical_id": canonical.memory_id,
        "lookup_alternate_id": lm.get(513) is not None,
        "corroborations_after_same_report_three_times": canonical.corroborations,
    }
    lm.ingest(message(host=2), extension(mid=513, version=2, state=MemoryState.CLEARED))
    result["merged_alias_clearance"] = {
        "canonical_state": lm.get(257).state.value,
        "alternate_id_stored": lm.get(513) is not None,
        "record_count": len(lm),
    }

    lm = LivingMap()
    lm.ingest(message(), extension())
    rec = lm.ingest(message(host=2), extension(version=2))
    result["host_migration"] = {
        "memory_id": rec.memory_id, "legacy_beacon_id": rec.beacon_id,
        "current_host_beacon_id": rec.host_beacon_id,
    }

    lm = LivingMap()
    lm.ingest(message(confidence=90), extension())
    lm.ingest(message(confidence=10), extension(version=2))
    result["lower_confidence_update"] = {
        "initial_confidence": lm.get(257).initial_confidence,
        "current_observed_confidence": lm.get(257).observed_confidence,
    }

    b = node(capacity=1)
    first = b.write_record(message(), extension())
    full = b.write_record(message(x=3), extension(mid=258))
    b.write_record(message(), extension(version=2, state=MemoryState.CLEARED))
    after_clear = b.write_record(message(x=3), extension(mid=258))
    result["beacon_capacity"] = {"first_write": first, "new_write_when_all_open": full,
                                 "new_write_after_closed_record": after_clear,
                                 "remaining_memory_ids": list(b.records)}

    b = node()
    b.write_record(message(), extension(version=255))
    raw = encode_memory_payload(message(), extension(version=256))
    decoded_message, decoded_ext = decode_memory_payload(raw)
    accepted = b.write_record(decoded_message, decoded_ext)
    result["version_wrap"] = {"attempted_version": 256, "wire_version": decoded_ext.version,
                              "accepted_against_version_255": accepted}
    result["memory_id_wrap"] = {
        "counter_1": memory_id_for(1, 1), "counter_257": memory_id_for(1, 257),
        "same_id": memory_id_for(1, 1) == memory_id_for(1, 257),
    }

    dispatcher = MissionDispatcher()
    rec = MemoryRecord.from_beacon_message(message())
    rec.memory_id = 257
    mr = dispatcher.on_new_record(rec, 0)
    dispatcher.assign(mr, "E01", 1)
    dispatcher.on_mission_failed("E01", 2)
    result["failed_mission_queue"] = {
        "queue_length": len(dispatcher._queue),
        "unique_object_count": len({id(x) for x in dispatcher._queue}),
        "mission_ids": [x.mission_id for x in dispatcher._queue],
    }

    brief = Mission("M001", policy=BlockagePolicy(max_wait_ticks=7),
                    memory_ref=257, version_ref=4, issued_tick=99)
    serialized = brief.to_dict()
    result["brief_serialization"] = {
        "exported_keys": sorted(serialized),
        "omitted_dataclass_fields": sorted({f.name for f in fields(Mission)} - set(serialized)),
    }
    ona = ONAGateway()
    ona.queue_brief("E01", Mission("M001"))
    ona.queue_brief("E01", Mission("M002"))
    result["mailbox_replace_and_consume"] = {
        "polled_mission": ona.poll_brief("E01").mission_id,
        "second_poll_is_none": ona.poll_brief("E01") is None,
    }

    from command_post.command_post import CommandPost
    cp = CommandPost(ONAGateway(), SimClock())
    cp.register_executor("E01", [])
    first_record = MemoryRecord.from_beacon_message(message())
    first_record.memory_id = 257
    first_mission = cp.dispatcher.on_new_record(first_record, 0)
    cp.dispatcher.assign(first_mission, "E01", 1)
    cp.dispatcher.finish(first_mission, 2, "VERIFIED")
    second_record = MemoryRecord.from_beacon_message(message(x=3))
    second_record.memory_id = 258
    second_mission = cp.dispatcher.on_new_record(second_record, 3)
    cp.dispatcher.assign(second_mission, "E01", 4)
    cp._status_seq["E01"] = 100
    stale = ExecStatus("E01", "RETURNING", 90, 257, MissionOutcome.VERIFIED)
    cp.on_status(UplinkStatus(stale, 0, 5, 99))
    result["late_previous_mission_outcome"] = {
        "old_memory_id": 257, "current_mission_memory_id": second_mission.beacon_id,
        "current_mission_state_after_old_report": second_mission.status.value,
        "stale_state_reports_dropped": cp.stats["stale_status_dropped"],
    }
    return result


def runtime_snapshot():
    from simulation.global_demo import run
    res = run(seed=42)
    system = res["system"]
    fresh = type(system)(system.scenario)
    return {
        "scenario": system.scenario.name,
        "command_post_records": [r.to_dict() for r in system.living_map.all()],
        "beacon_records": [
            {"host": bid, "memory_id": mid, "version": ext.version,
             "state": ext.state.value, "source_node": ext.source}
            for bid, b in system.beacons.nodes.items()
            for mid, (_, ext) in b.records.items()
        ],
        "mission_records": [{f.name: getattr(m, f.name) for f in fields(MissionRecord)}
                            for m in system.command_post.mission_table()],
        "fresh_system_record_count": len(fresh.living_map),
        "fresh_system_beacon_count": len(fresh.beacons.nodes),
    }


if __name__ == "__main__":
    models = [BeaconMessage, MemoryExt, ProgramCommand, MemoryRecord, BeaconHealth,
              MissionRecord, FleetEntry, Mission, MissionTarget, HazardHint, BlockagePolicy]
    evidence = {
        "model_fields": {cls.__name__: [{"name": f.name, "type": str(f.type)} for f in fields(cls)]
                         for cls in models},
        "probes": probes(),
        "runtime": runtime_snapshot(),
    }
    print(json.dumps(evidence, indent=2, default=lambda x: x.value if hasattr(x, "value") else str(x)))
