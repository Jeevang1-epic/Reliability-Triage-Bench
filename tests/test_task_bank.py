from task_bank import evaluate_submission, get_task, list_task_names


def test_all_tasks_registered() -> None:
    names = list_task_names()
    assert "easy_api_latency_spike" in names
    assert "medium_payment_processor_outage" in names
    assert "hard_credential_compromise" in names
    assert len(names) >= 3


def test_perfect_submission_scores_one() -> None:
    for task_name in list_task_names():
        task = get_task(task_name)
        note = " ".join(task.keyword_targets)
        result = evaluate_submission(task, task.required_fields, note)
        assert result["score"] == 1.0


def test_incorrect_submission_scores_lower() -> None:
    task = get_task("medium_payment_processor_outage")
    bad_decisions = {
        "severity": "sev3",
        "owner_team": "api-platform",
        "incident_type": "latency-regression",
        "first_action": "rollback-canary",
        "customer_impact": "degraded-search",
        "escalation_target": "none",
    }
    result = evaluate_submission(task, bad_decisions, "short note")
    assert 0.0 <= result["score"] < 0.4
