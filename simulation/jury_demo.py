"""Shared guided/headless Phase 1 demonstrations, driven by runtime predicates.

This controller is simulator-side. It never supplies ground truth to robots
or to the Command Post. Scenario injections use the existing world doorways.
"""
from __future__ import annotations

import argparse
from collections import deque
import json
from pathlib import Path
import time

from common.enums import EventType, MemoryState, MissionStatus, ExecutorState
from common.protocol import MeshFrame, FrameType, DecodeError, decode_memory_payload
from simulation.phase1 import build_scenario, CHALLENGE_TYPES, pick_debris, all_idle
from simulation.system import LiveMapSystem

SCENARIOS = ("normal", "writer-failure", "debris-recovery")


class JurySession:
    def __init__(self, scenario="normal", seed=42, guard=60_000):
        if scenario not in SCENARIOS:
            raise ValueError(f"unknown guided scenario: {scenario}")
        self.name, self.seed, self.guard = scenario, seed, guard
        debris = scenario == "debris-recovery"
        sc = build_scenario(f"jury-{scenario}", seed,
                            [EventType.FIRE] if debris else CHALLENGE_TYPES,
                            fleet={"FIRE": 2, "DEBRIS": 1} if debris else {"FIRE": 1, "GAS": 1},
                            jitter=0 if debris else 0.4,
                            writer_fail_tick=1500 if scenario == "writer-failure" else None,
                            dispatch_threshold=0)
        self.system = LiveMapSystem(sc)
        self.packets = deque(maxlen=128)
        self.system.medium.log_hook = self._packet
        self.writer = self.system.deploy_writer()
        self.paused = True
        self.done = False
        self.error = None
        self.error_detail = None
        self.stage = 0
        self.writer_done_tick = None
        self.settled_since = None
        self.new_debris = []
        middle = ["Blocked target: clearance requested", "Clearance observed; retry follows", "Target resolved on retry"] if debris else ["Executor observations preserved"]
        self.labels = ["Ready: start Writer exploration", "Memory preserved in beacons",
                       "Writer stopped; inherited memory at Command Post", "Missions assigned through ONA",
                       *middle, "Complete: outcomes received and executors home"]
        self.checkpoints = [{"tick": 0, "name": self.label}]

    @property
    def label(self):
        return self.explanation()["title"]

    def explanation(self):
        from simulation.demo_language import explanation
        return explanation(self)

    def _fail(self, reason, detail=None):
        self.error, self.error_detail = reason, detail
        self.done, self.paused = False, True
        self.checkpoints.append({"tick": self.system.tick, "name": self.label, "error": reason})

    def _timeout_reason(self):
        sys = self.system
        if not any(n.records for n in sys.beacons.nodes.values()):
            reason = ("the explorer stopped before any findings were saved" if self.writer.dead
                      else "the explorer had not yet saved a finding")
        elif self.stage == 1:
            reason = "the outside team has not received all required findings"
        elif self.stage == 2:
            reason = "the response robots have not received their instructions"
        elif any(e.state == ExecutorState.OUT_OF_SERVICE and e.capabilities[0].value == "DEBRIS"
                 for e in sys.executors) and self.name == "debris-recovery":
            reason = "the route is blocked and the rubble removal robot is out of service"
        elif any(e.state in (ExecutorState.NEEDS_REPAIR, ExecutorState.NEEDS_CHARGING, ExecutorState.OUT_OF_SERVICE)
                 for e in sys.executors):
            from simulation.demo_language import ROBOT_STATES
            robot = next(e for e in sys.executors if e.state in (ExecutorState.NEEDS_REPAIR, ExecutorState.NEEDS_CHARGING, ExecutorState.OUT_OF_SERVICE))
            reason = f"{robot.executor_id} {ROBOT_STATES[robot.state.value]}; the demo's return and job checks remain unfinished"
        elif any(not e.at_entry for e in sys.executors):
            reason = "a response robot has not returned to the entrance"
        else:
            reason = "the required job results or final radio updates have not arrived"
        return f"The time limit was reached while {reason}."

    def _packet(self, tick, src, dst, raw):
        if dst != 0:
            return
        try:
            frame = MeshFrame.decode(raw)
            if frame.ftype != FrameType.MEMORY:
                return
            msg, ext = decode_memory_payload(frame.payload)
        except DecodeError:
            return
        self.packets.append(dict(tick=tick, src=src, dst=dst, origin=frame.origin,
                                 seq=frame.seq, hops=frame.hop_count, bytes=len(raw),
                                 hex=raw.hex(" "), memory_id=ext.memory_id, version=ext.version,
                                 state=ext.state.value, host=msg.beacon_id))

    def packet_for(self, record):
        return next((p for p in reversed(self.packets)
                     if p["memory_id"] in [record.memory_id, *record.aliases]), None)

    def advance(self):
        if self.done or self.error:
            return
        if self.stage == 2:
            if self.name == "debris-recovery" and not self.new_debris:
                target = self.system.scenario.events[0]
                self.new_debris = pick_debris(self.system.world, self.seed, "seal",
                                             self.system.world.entry, (target.row, target.col))
                for cell in self.new_debris:
                    if not self.system.add_debris(cell, "guided-after-writer"):
                        self._fail("The demo could not add the planned blocked route.", f"debris cell {cell}")
                        return
            self.system.auto_dispatch = True
        self.paused = False

    def toggle_pause(self):
        if not self.done and not self.error:
            if self.paused:
                self.advance()
            else:
                self.paused = True

    def reset(self, scenario=None):
        self.__init__(scenario or self.name, self.seed, self.guard)

    def _resolved(self):
        records = self.system.living_map.all()
        expected = {"FIRE": MemoryState.CLEARED, "GAS": MemoryState.ACTIVE}
        types = {"FIRE"} if self.name == "debris-recovery" else set(expected)
        return all(any(r.event_type == typ and r.state == expected[typ] and r.version >= 2
                       for r in records) for typ in types)

    def _complete(self):
        sys = self.system
        missions = sys.command_post.mission_table()
        return (self._resolved() and bool(missions)
                and all(m.status == MissionStatus.COMPLETED for m in missions if m.attempt_id)
                and not sys.command_post.ranked_missions(auto=True)
                and all_idle(sys) and all(e.at_entry and e.state == ExecutorState.AVAILABLE for e in sys.executors)
                and all(e.available for e in sys.command_post.fleet.all()))

    def step(self):
        if self.paused or self.done or self.error:
            return
        sys = self.system
        try:
            sys.update()       # drains final transport even when system.phase == complete
        except Exception as exc:
            self._fail("The simulation stopped because an unexpected error occurred.", f"{type(exc).__name__}: {exc}")
            return
        if sys.tick > self.guard:
            self._fail(self._timeout_reason(), f"timeout tick={sys.tick}, stage={self.stage}")
            return
        if self.writer.dead and self.writer_done_tick is None:
            self.writer_done_tick = sys.tick
        records = sys.living_map.all()
        if self.stage == 0:
            ready = any(n.records for n in sys.beacons.nodes.values())
        elif self.stage == 1:
            types = {"FIRE"} if self.name == "debris-recovery" else {"FIRE", "GAS"}
            ready = (self.writer_done_tick is not None and sys.tick >= self.writer_done_tick + 400
                     and types <= {r.event_type for r in records})
        elif self.stage == 2:
            ready = (bool(sys.command_post.decisions) and sys.ona.briefs_delivered > 0
                     and any(e.stats["missions"] > 0 for e in sys.executors))
        elif self.name == "debris-recovery" and self.stage == 3:
            ready = any(m.event_type == "FIRE" and m.status == MissionStatus.BLOCKED
                        for m in sys.command_post.mission_table())
        elif self.name == "debris-recovery" and self.stage == 4:
            ready = any(r.event_type == "BLOCKAGE" and r.state == MemoryState.CLEARED for r in records)
        elif self.stage == len(self.labels) - 2:
            complete = self._complete()
            self.settled_since = (self.settled_since if self.settled_since is not None else sys.tick) if complete else None
            ready = self.settled_since is not None and sys.tick - self.settled_since >= 60
        else:
            ready = self._resolved()
        if ready:
            self.stage += 1
            self.paused = True
            self.done = self.stage == len(self.labels) - 1
            if self.done:
                failed = [name for name, passed in self.checks().items() if not passed]
                if failed:
                    reasons = {"beacon_updates_agree": "The saved radio marker copies disagree with the outside team's final findings.",
                               "two_distinct_fire_attempts": "The fire job did not have exactly one separate retry.",
                               "writer_end": "The explorer did not finish in the way this test requires.",
                               "queue_unique": "A job appears more than once in the waiting queue."}
                    self._fail(reasons.get(failed[0], "A required final demonstration check failed."), ", ".join(failed))
                    return
            self.checkpoints.append({"tick": sys.tick, "name": self.label})

    def checks(self):
        sys = self.system
        missions = sys.command_post.mission_table()
        checks = {"all_milestones": self.done and not self.error,
                  "final_memory_states": self._resolved(),
                  "missions_completed_and_home": self._complete(),
                  "writer_end": self.writer.dead and (not self.writer.returned if self.name == "writer-failure" else self.writer.returned),
                  "ona_path": sys.ona.mesh_stats["memory"] > 0 and sys.ona.briefs_delivered > 0,
                  "queue_unique": len({m.mission_id for m in sys.mission_dispatcher._queue}) == len(sys.mission_dispatcher._queue)}
        if self.name == "debris-recovery":
            fire = [d for d in sys.command_post.decisions if d["event_type"] == "FIRE"]
            checks["two_distinct_fire_attempts"] = len(fire) == 2 and fire[0]["attempt_id"] != fire[1]["attempt_id"]
            checks["debris_executor_used"] = any(d["event_type"] == "BLOCKAGE" for d in sys.command_post.decisions)
            checks["clearance_received"] = any(r.event_type == "BLOCKAGE" and r.state == MemoryState.CLEARED for r in sys.living_map.all())
        checks["beacon_updates_agree"] = all(
            (node := sys.beacons.nodes.get(r.host_beacon_id)) is not None
            and r.memory_id in node.records and node.records[r.memory_id][1].state == r.state
            for r in sys.living_map.all())
        return checks

    def report(self):
        checks = self.checks()
        return dict(scenario=self.name, seed=self.seed, passed=all(checks.values()), error=self.error,
                    explanation=self.explanation(), error_detail=self.error_detail,
                    checks=checks, tick=self.system.tick, checkpoints=self.checkpoints,
                    records=[r.to_dict() for r in self.system.living_map.all()],
                    decisions=self.system.command_post.decisions, network=self.system.network_report(),
                    writer_state=self.writer.state.value,
                    writer_decisions=list(self.writer.decisions),
                    executor_events={e.executor_id: e.events for e in self.system.executors},
                    packets=list(self.packets))


def run(scenario="normal", seed=42, guard=60_000, capture=None):
    session = JurySession(scenario, seed, guard)
    started = time.perf_counter()
    if capture:
        capture(session)
    while not session.done and not session.error:
        if session.paused:
            session.advance()
        checkpoint = len(session.checkpoints)
        session.step()
        if capture and len(session.checkpoints) != checkpoint:
            capture(session)
    result = session.report()
    result["wall_seconds"] = round(time.perf_counter() - started, 3)
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scenario", choices=[*SCENARIOS, "all"], default="all")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--guard", type=int, default=60_000)
    ap.add_argument("--output", type=Path)
    ap.add_argument("--capture-dir", type=Path)
    args = ap.parse_args(argv)
    capture = None
    if args.capture_dir:
        import os
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
        from simulation.renderer import Renderer
        import pygame
        args.capture_dir.mkdir(parents=True, exist_ok=True)
        def capture(session):
            renderer = Renderer(session.system, session)
            for tab in ("Mission", "Memory"):
                renderer.inspector.set_tab(tab)
                renderer.draw()
                suffix = "-failed" if session.error else ""
                pygame.image.save(renderer.screen, str(args.capture_dir / f"{session.name}-{session.stage:02d}-{tab.lower()}{suffix}.png"))
    names = SCENARIOS if args.scenario == "all" else [args.scenario]
    results = [run(name, args.seed, args.guard, capture) for name in names]
    payload = dict(passed=all(r["passed"] for r in results), results=results)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    for r in results:
        print(f"{r['scenario']}: {'PASS' if r['passed'] else 'FAIL'} tick={r['tick']} checks={r['checks']}")
    return 0 if payload["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
