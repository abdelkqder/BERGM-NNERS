"""Deliberate failures must stop the guided demo, never show success."""
import pytest

from common.enums import ExecutorState, MemoryState
from simulation.jury_demo import JurySession

FAILURES = ("early-writer", "outside-link", "missing-brief", "no-clearer", "robot-fault",
            "low-battery", "stranded-robot", "conflicting-copy", "extra-retry", "robot-not-home", "runtime-error")


def finish(session, until=None):
    while not session.done and not session.error:
        if until and until(session):
            return session
        if session.paused:
            session.advance()
        session.step()
    return session


def failure_case(name):
    s = JurySession("debris-recovery" if name in ("no-clearer", "extra-retry") else "normal", guard=6500)
    fire = next(e for e in s.system.executors if e.capabilities[0].value == "FIRE")
    if name == "early-writer":
        s.writer.force_fail()
    elif name == "outside-link":
        s.system.ona._memory_fn = lambda _: False
    elif name == "missing-brief":
        for e in s.system.executors:
            e.briefing_poll = lambda _: None
    elif name == "no-clearer":
        next(e for e in s.system.executors if e.capabilities[0].value == "DEBRIS")._set_state(ExecutorState.OUT_OF_SERVICE)
    elif name in ("robot-fault", "stranded-robot"):
        fire.fault_at_tick = 40
        fire.fault_strands = name == "stranded-robot"
    elif name == "low-battery":
        fire.battery_drain = 10
    elif name in ("conflicting-copy", "extra-retry", "robot-not-home"):
        finish(s, lambda s: s.stage == len(s.labels)-2)
        assert not s.error and not s.done
        if name == "conflicting-copy":
            rec = next(r for r in s.system.living_map.all() if r.event_type == "FIRE")
            s.system.beacons.nodes[rec.host_beacon_id].records[rec.memory_id][1].state = MemoryState.UNVERIFIED
        elif name == "extra-retry":
            s.system.command_post.decisions.append(dict(s.system.command_post.decisions[-1]))
        else:
            fire.movement.teleport((1, 2))
            fire._state = ExecutorState.OUT_OF_SERVICE
            fire._finished = True
    elif name == "runtime-error":
        def broken_update():
            raise RuntimeError("deliberate diagnostic failure")
        s.system.update = broken_update
    else:
        raise ValueError(name)
    return s


@pytest.mark.parametrize("name", FAILURES)
def test_injected_failure_is_stopped_and_explained(name):
    s = finish(failure_case(name))
    result = s.report()
    assert not result["passed"] and not s.done and s.paused and s.error, result
    explanation = s.explanation()
    assert explanation["status"] == "stopped"
    assert explanation["what"] and explanation["next"]
    assert "success" not in explanation["title"].lower()
    tick = s.system.tick
    s.advance()
    s.step()
    assert s.system.tick == tick, "a failed demo must not silently resume"


def test_all_stages_have_plain_language_explanations():
    for name in ("normal", "writer-failure", "debris-recovery"):
        s = JurySession(name)
        for stage in range(len(s.labels)):
            s.stage = stage
            text = s.explanation()
            assert all(text[k] for k in ("title", "what", "why", "next"))
            assert not any(term in text["what"] for term in ("UNVERIFIED", "TTL", "CRC", "frontier", "ONA"))
