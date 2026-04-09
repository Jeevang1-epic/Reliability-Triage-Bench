from models import ReliabilityTriageAction
from server.reliability_triage_environment import ReliabilityTriageEnvironment
from task_bank import get_task


def _solve_task(env: ReliabilityTriageEnvironment, task_name: str) -> float:
    task = get_task(task_name)
    env.reset(task_name=task_name)
    env.step(ReliabilityTriageAction(command="view_brief"))
    for signal_id in sorted(task.signals.keys()):
        if signal_id != "signal-1":
            env.step(ReliabilityTriageAction(command="view_signal", signal_id=signal_id))
    for field, value in task.required_fields.items():
        env.step(ReliabilityTriageAction(command="set_field", field=field, value=value))
    env.step(
        ReliabilityTriageAction(command="append_note", note=" ".join(task.keyword_targets))
    )
    final = env.step(ReliabilityTriageAction(command="submit"))
    return float(final.metadata.get("score", 0.0))


def test_perfect_policy_scores_high() -> None:
    env = ReliabilityTriageEnvironment()
    for task_name in [
        "easy_api_latency_spike",
        "medium_payment_processor_outage",
        "hard_credential_compromise",
    ]:
        score = _solve_task(env, task_name)
        assert score >= 0.95


def test_invalid_action_penalty() -> None:
    env = ReliabilityTriageEnvironment()
    env.reset(task_name="easy_api_latency_spike")
    result = env.step(ReliabilityTriageAction(command="set_field", field="severity"))
    assert result.reward is not None
    assert result.reward < 0.0
