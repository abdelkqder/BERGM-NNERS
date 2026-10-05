import pytest
from simulation.jury_demo import JurySession, SCENARIOS, run


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_guided_and_headless_scenarios_reach_real_completion(scenario):
    result = run(scenario)
    assert result["passed"], result["checks"]
    assert all(result["checks"].values())
    assert result["packets"] and result["writer_decisions"]


def test_timeout_is_a_failure_and_cannot_be_resumed_into_success():
    s=JurySession(guard=2)
    s.advance()
    for _ in range(5):
        s.step()
    assert s.error and not s.report()["passed"]
    s.advance()
    assert s.paused


def test_pause_and_reset_do_not_advance_the_world():
    s=JurySession()
    s.step()
    assert s.system.tick==0
    s.advance()
    s.step()
    s.toggle_pause()
    s.step()
    assert s.system.tick==1
    s.reset()
    assert s.system.tick==0 and s.stage==0 and s.paused
