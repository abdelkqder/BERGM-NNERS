"""Regressions for the observed Phase 1 data and assignment failures."""
import pytest

from command_post.map_state import LivingMap
from common.enums import MemoryState, MissionStatus, ExecutorState
from common.protocol import (
    BeaconMessage, MemoryExt, ExecStatus, MissionOutcome, EXEC_STATE_CODES,
    encode_status, decode_status, DecodeError, encode_memory_payload, memory_id_for,
    writer_node_id, executor_node_id,
)
from gateway.ona_gateway import UplinkStatus, UplinkMemory
from simulation.phase1 import build_scenario, CHALLENGE_TYPES
from simulation.system import LiveMapSystem

TS = 1790000000


def observation(lm, mid=257, ver=1, state=MemoryState.UNVERIFIED, ts=TS, host=1, x=1):
    return lm.ingest(BeaconMessage(host, "FIRE", x, 2, TS, 3, 90, 100),
                     MemoryExt(mid, ver, state, None, ts, 65))


def test_alias_is_addressable_and_repeated_copies_do_not_corroborate():
    lm = LivingMap()
    first = observation(lm)
    observation(lm, mid=513)
    observation(lm, mid=513)
    assert lm.get(513) is first
    assert len(lm) == 1 and first.corroborations == 1


@pytest.mark.parametrize("state", [MemoryState.CLEARED, MemoryState.CONTRADICTED])
def test_alias_can_resolve_an_event_and_old_reports_cannot_reopen_it(state):
    lm = LivingMap()
    first = observation(lm)
    observation(lm, mid=513)
    observation(lm, mid=513, ver=2, state=state, ts=TS+10)
    assert first.state == state
    revision = first.version
    observation(lm, ver=2, ts=TS+5)
    observation(lm, ver=3, ts=TS+10)
    assert first.state == state and first.version == revision


def test_same_stream_older_timestamp_is_rejected_and_host_tracks_latest_write():
    lm = LivingMap()
    first = observation(lm)
    observation(lm, ver=2, state=MemoryState.VERIFIED, ts=TS+10, host=2)
    assert first.beacon_id == first.host_beacon_id == 2
    observation(lm, ver=3, ts=TS+5)
    assert first.state == MemoryState.VERIFIED and first.observed_ts == TS+10


def cp_with_records():
    sys = LiveMapSystem(build_scenario("repairs", 42, CHALLENGE_TYPES,
                                    fleet={"FIRE": 1}, dispatch_threshold=0))
    cp = sys.command_post
    observation(cp.living_map)
    observation(cp.living_map, mid=258, x=5)
    for rec in cp.living_map.all():
        cp.dispatcher.on_new_record(rec, 0)
    return cp


def test_failure_requeues_one_copy():
    cp = cp_with_records()
    mr = cp.dispatcher.next_queued()
    cp.dispatcher.assign(mr, "E01", 1)
    cp.dispatcher.on_mission_failed("E01", 2)
    assert sum(m.mission_id == mr.mission_id for m in cp.dispatcher._queue) == 1


def test_legacy_delayed_outcome_does_not_close_another_memory():
    cp = cp_with_records()
    first, second = cp.dispatcher.all_missions()
    cp.dispatcher.assign(first, "E01", 1)
    cp.dispatcher.finish(first, 2, "CLEARED")
    cp.dispatcher.assign(second, "E01", 3)
    cp._status_seq["E01"] = 100
    cp.on_status(UplinkStatus(ExecStatus("E01", "RETURNING", 100, first.beacon_id,
                                        MissionOutcome.CLEARED), 0, 4, 99))
    assert second.status == MissionStatus.ASSIGNED


def test_status_supports_both_lengths_and_rejects_ambiguous_extensions():
    legacy = ExecStatus("E01", "AVAILABLE")
    raw = encode_status(legacy, EXEC_STATE_CODES)
    assert len(raw) == 9 and decode_status(raw, EXEC_STATE_CODES).attempt_id == 0
    modern = ExecStatus("E01", "RETURNING", 90, 257, MissionOutcome.CLEARED, attempt_id=12)
    encoded = encode_status(modern, EXEC_STATE_CODES)
    assert len(encoded) == 11 and decode_status(encoded, EXEC_STATE_CODES) == modern
    for bad in (raw[:-1], raw+b"x", encoded+b"x"):
        with pytest.raises(DecodeError):
            decode_status(bad, EXEC_STATE_CODES)


@pytest.mark.parametrize("call", [lambda: memory_id_for(1, 256), lambda: memory_id_for(256, 1),
                                  lambda: writer_node_id(16), lambda: executor_node_id(64),
                                  lambda: encode_memory_payload(BeaconMessage(1, "FIRE", 0, 0, TS, 3, 90, 100),
                                                                MemoryExt(257, 256))])
def test_identity_and_version_exhaustion_is_explicit(call):
    with pytest.raises(ValueError):
        call()


def status(cp, mr, sequence, outcome=MissionOutcome.NONE, state="RETURNING", memory=None, attempt=None):
    cp.on_status(UplinkStatus(ExecStatus("E01", state, 90,
                                        mr.beacon_id if memory is None else memory, outcome,
                                        mr.attempt_id if attempt is None else attempt), 0, 0, sequence))


def test_matching_late_outcome_closes_own_mission_without_rolling_back_state():
    cp = cp_with_records()
    cp.dispatch_next()
    mr = cp._mission_of("E01")
    status(cp, mr, 100, state="AVAILABLE")
    status(cp, mr, 99, MissionOutcome.CLEARED)
    status(cp, mr, 101, MissionOutcome.CLEARED, state="AVAILABLE")
    assert mr.status == MissionStatus.COMPLETED
    assert cp.fleet.get("E01").state == ExecutorState.AVAILABLE
    assert cp.fleet.get("E01").missions_done == 1


def test_late_previous_assignment_result_never_releases_new_assignment():
    cp = cp_with_records()
    cp.dispatch_next()
    first = cp._mission_of("E01")
    status(cp, first, 100, state="AVAILABLE")
    cp.dispatch_next()
    second = cp.dispatcher.next_queued() or cp.dispatcher._active["E01"]
    assert second is not first and second.attempt_id != first.attempt_id
    status(cp, first, 99, MissionOutcome.CLEARED, state="AVAILABLE")
    assert first.status == MissionStatus.COMPLETED and second.status == MissionStatus.ASSIGNED
    assert cp.fleet.get("E01").mission_id == second.mission_id
    assert cp.fleet.get("E01").reserved
    status(cp, second, 101, MissionOutcome.CLEARED, attempt=0)
    assert second.status == MissionStatus.ASSIGNED


def test_retry_uses_new_attempt_and_ignores_previous_attempt_outcome():
    cp = cp_with_records()
    cp.dispatch_next()
    mr = cp._mission_of("E01")
    old = mr.attempt_id
    status(cp, mr, 1, MissionOutcome.FAILED, state="AVAILABLE")
    assert cp.dispatcher.queued_count == 2
    cp.dispatch_next()
    assert mr.attempt_id != old
    status(cp, mr, 2, MissionOutcome.CLEARED, attempt=old)
    assert mr.status == MissionStatus.ASSIGNED
    status(cp, mr, 3, MissionOutcome.BLOCKED, memory=1025)
    assert mr.status == MissionStatus.BLOCKED and cp.waiting_on[1025] == [mr.mission_id]
    status(cp, mr, 4, MissionOutcome.BLOCKED, memory=1025)
    assert cp.waiting_on[1025] == [mr.mission_id]


def test_sequence_wrap_is_newer_but_duplicate_sequence_does_not_rollback_state():
    cp = cp_with_records()
    cp.dispatch_next()
    mr = cp._mission_of("E01")
    status(cp, mr, 65535, state="DEPLOYING")
    status(cp, mr, 0, state="WORKING")
    status(cp, mr, 0, state="DEPLOYING")
    assert cp.fleet.get("E01").state == ExecutorState.WORKING


def test_diagnostic_exports_include_brief_and_observation_provenance():
    cp = cp_with_records()
    cp.dispatch_next()
    brief = cp.ona._mailbox["E01"].to_dict()
    assert brief["attempt_id"] > 0 and "policy" in brief and "issued_tick" in brief
    rec = cp.living_map.all()[0].to_dict()
    assert rec["timestamp"] == TS and rec["source_node"] == 65 and "aliases" in rec


def test_blockage_dependency_learned_before_alias_is_canonicalized():
    cp = cp_with_records()
    cp.waiting_on[513] = ["M001"]
    observation(cp.living_map)
    cp.on_memory(UplinkMemory(BeaconMessage(1,"FIRE",1,2,TS,3,90,100),
                              MemoryExt(513,1,MemoryState.UNVERIFIED,None,TS,65),0,1,0,TS))
    assert cp.waiting_on[257] == ["M001"] and 513 not in cp.waiting_on


def test_clearance_received_before_blocked_status_unblocks_without_another_packet():
    cp = cp_with_records()
    cp.dispatch_next()
    mr = cp._mission_of("E01")
    cp.living_map.ingest(BeaconMessage(1,"BLOCKAGE",9,2,TS,3,90,100),
                         MemoryExt(1025,2,MemoryState.CLEARED,None,TS,130))
    status(cp,mr,1,MissionOutcome.BLOCKED,memory=1025)
    assert mr.status == MissionStatus.QUEUED and not cp.waiting_on
