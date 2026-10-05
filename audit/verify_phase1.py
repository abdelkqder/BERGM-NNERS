"""Supplementary failure checks and real Pygame event/render evidence.

Run from the repository root: python -B audit/verify_phase1.py [--native]
The relay diagnostic reuses the existing isolated unit-test chain fixture.
"""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from common.enums import EventType, MemoryState
from simulation.phase1 import build_scenario, explore_phase, run_until, all_idle, run_ticks
from simulation.system import LiveMapSystem
from simulation.jury_demo import JurySession, SCENARIOS


def observation_checks():
    sys_=LiveMapSystem(build_scenario("aging",42,[EventType.FIRE],fleet={"FIRE":1},dispatch_threshold=0))
    explore_phase(sys_)
    rec=sys_.living_map.all()[0]
    before=rec.to_dict()
    sys_.skip_time(1200)
    aged=rec.to_dict()
    sys_.auto_dispatch=True
    finished=run_until(sys_,lambda s: all_idle(s) and bool(s.command_post.decisions) and rec.state==MemoryState.CLEARED)
    run_ticks(sys_,60)
    refreshed=rec.to_dict()
    checks=dict(age_decay=aged['live_confidence_pct']<before['live_confidence_pct'],
                stale_without_lifecycle_change=aged['is_stale'] and aged['state']==before['state'],
                executor_refresh=finished and refreshed['version']>aged['version'] and refreshed['age_s']<aged['age_s'])
    absent=LiveMapSystem(build_scenario("contradiction",42,[EventType.FIRE],fleet={"FIRE":1},dispatch_threshold=0))
    explore_phase(absent)
    absent.world.resolve_event(absent.scenario.events[0].id,absent.tick)   # simulator injection only
    absent.auto_dispatch=True
    confirmed=run_until(absent,lambda s: all_idle(s) and bool(s.command_post.decisions)
                        and s.living_map.all()[0].state==MemoryState.CONTRADICTED)
    run_ticks(absent,60)
    checks['contradiction_by_sensing']=confirmed and any(e['kind']=='not_found' for ex in absent.executors for e in ex.events)
    return dict(checks=checks, aging=dict(before=before,aged=aged,refreshed=refreshed),
                contradiction=dict(record=absent.living_map.all()[0].to_dict(),
                                   events=absent.executors[0].events))


def relay_check():
    from tests.test_mesh_network import build_chain,run,program
    from common.protocol import FrameType,decode_memory_payload
    med,ona,nodes,received=build_chain([3,6,9,12])
    run(med,ona,nodes,200)
    original=[n.hops for n in nodes]
    nodes[1].alive=False
    med.set_alive(2,False)
    run(med,ona,nodes,500,start=201)
    received.clear()
    assert program(med,4,col=13)
    run(med,ona,nodes,100,start=701)
    outage=dict(connected=nodes[3].connected, stored=1 in nodes[3].records,
                delivered=bool([f for f in received if f.ftype==FrameType.MEMORY]),
                buffered=len(nodes[3]._queue))
    nodes[1].alive=True
    med.set_alive(2,True)
    run(med,ona,nodes,600,start=801)
    frames=[f for f in received if f.ftype==FrameType.MEMORY]
    checks=dict(chain_formed=original==[1,2,3,4], retained_while_disconnected=outage['stored'] and not outage['delivered'],
                delivered_after_reconnect=bool(frames) and decode_memory_payload(frames[-1].payload)[1].memory_id==1,
                source_copy_survives=1 in nodes[3].records)
    return dict(checks=checks,original_hops=original,outage=outage,restored_hops=[n.hops for n in nodes],
                received_frames=[f.encode().hex(' ') for f in frames],
                stats=[dict(n.stats.__dict__) for n in nodes])


def ui_checks(native=False):
    if not native:
        os.environ['SDL_VIDEODRIVER']='dummy'
    os.environ['SDL_AUDIODRIVER']='dummy'
    from simulation.renderer import Renderer
    import pygame
    dest=ROOT/'audit/phase1/ui'
    dest.mkdir(parents=True,exist_ok=True)
    results=[]
    session=JurySession()
    r=Renderer(session.system,session)
    def key(k):
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN,key=k))
        for ev in pygame.event.get():
            assert r.inspector.handle_event(ev)
    for i,name in enumerate(SCENARIOS):
        key(pygame.K_1+i)
        assert session.name==name and session.paused and session.stage==0
        key(pygame.K_SPACE)
        session.step()
        key(pygame.K_p)
        paused_tick=session.system.tick
        session.step()
        assert session.paused and session.system.tick==paused_tick
        key(pygame.K_p)
        while not session.done and not session.error:
            if session.paused:
                key(pygame.K_SPACE)
            session.step()
        assert session.report()['passed'],session.report()['checks']
        key(pygame.K_r)
        assert session.paused and session.stage==0 and session.system.tick==0
        # Re-run through the same controller to capture final views after reset.
        while not session.done and not session.error:
            if session.paused:key(pygame.K_SPACE)
            session.step()
        captures=[]
        for tab in ('Mission','Memory'):
            r.inspector.details=False
            r.inspector.set_tab(tab)
            r.draw()
            assert all(r.font_sm.size(line)[0]<=r.panel_w-32 for line,_ in r.inspector.content_lines)
            assert all(rect.bottom<=r.h for rect,_ in r._buttons)
            path=dest/f'{name}-{tab.lower()}.png'
            pygame.image.save(r.screen,str(path));captures.append(str(path.relative_to(ROOT)))
            if tab=='Memory':
                # Actual mouse row selection and scroll input.
                target=session.system.living_map.all()[-1].memory_id
                record_rects=[rect for rect,_ in r._buttons if rect.width==r.panel_w-24]
                rect=record_rects[-1]
                pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=rect.center))
                for ev in pygame.event.get():r.inspector.handle_event(ev)
                assert r._selected==target
                r.draw()
                pygame.image.save(r.screen,str(dest/f'{name}-selected-memory.png'))
            key(pygame.K_t)
            assert r.inspector.details
            r.draw()
            assert all(r.font_sm.size(line)[0]<=r.panel_w-32 for line,_ in r.inspector.content_lines)
            pygame.image.save(r.screen,str(dest/f'{name}-{tab.lower()}-details.png'))
            pygame.event.post(pygame.event.Event(pygame.MOUSEWHEEL,y=-20,x=0))
            for ev in pygame.event.get():r.inspector.handle_event(ev)
            r.draw()
            assert r.inspector.visible_lines[-1]==r.inspector.content_lines[-1]
            pygame.image.save(r.screen,str(dest/f'{name}-{tab.lower()}-lower.png'))
        key(pygame.K_TAB)
        assert r.inspector.tab=='Mission'
        results.append(dict(scenario=name,passed=True,controls=['scenario selection','advance','pause','resume','reset','tabs','details toggle','record selection','scroll'],captures=captures))
    from tests.test_jury_failures import FAILURES, failure_case, finish
    failures=[]
    for name in FAILURES:
        failed=finish(failure_case(name))
        assert failed.error and not failed.done and not failed.report()['passed']
        r.sys, r.inspector.session = failed.system, failed
        r._selected=None
        r.inspector.details=False
        r.inspector.set_tab('Mission')
        r.draw()
        assert all(rect.bottom<=r.h for rect,_ in r._buttons)
        path=dest/f'failure-{name}.png'
        pygame.image.save(r.screen,str(path))
        failures.append(dict(case=name,correctly_stopped=True,tick=failed.system.tick,
                             explanation=failed.explanation(),diagnostic=failed.error_detail,
                             failed_checks=[k for k,v in failed.checks().items() if not v],
                             capture=str(path.relative_to(ROOT))))
    driver=pygame.display.get_driver()
    pygame.quit()
    return dict(driver=driver,native=native,results=results,deliberate_failures=failures)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--native',action='store_true')
    args=ap.parse_args()
    observation=observation_checks()
    relay=relay_check()
    ui=ui_checks(args.native)
    from simulation.global_demo import run as global_run
    from simulation.compare_memory import run as compare
    deep=global_run(5)
    comparison=compare(6)
    checks={**observation['checks'],**relay['checks'],
            'deep_chain':deep['network']['max_hops']>=4,
            'comparison_six_seeds':len(comparison['runs'])==6,
            'comparison_targets_reached':all(row[mode]['reached_target'] for row in comparison['runs'] for mode in ('memory','baseline')),
            'ui_controls':all(r['passed'] for r in ui['results']),
            'deliberate_failures_stop':len(ui['deliberate_failures'])==11 and all(r['correctly_stopped'] for r in ui['deliberate_failures'])}
    payload=dict(passed=all(checks.values()),checks=checks,observation=observation,relay=relay,ui=ui,
                 deep_chain=deep['network'],comparison=comparison)
    path=ROOT/'audit/phase1/supplemental.json'
    path.write_text(json.dumps(payload,indent=2),encoding='utf-8')
    print(json.dumps(dict(passed=payload['passed'],checks=checks,ui_driver=ui['driver']),indent=2))
    return 0 if payload['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
