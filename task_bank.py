from dataclasses import dataclass
from typing import Dict, List, Literal


DifficultyLevel = Literal["easy", "medium", "hard"]

SEVERITY_ORDER = ["sev0", "sev1", "sev2", "sev3"]

VALUE_ALIASES: Dict[str, Dict[str, str]] = {
    "severity": {
        "critical": "sev0",
        "sev-0": "sev0",
        "sev-1": "sev1",
        "sev-2": "sev2",
        "sev-3": "sev3",
        "high": "sev1",
        "medium": "sev2",
        "low": "sev3",
    },
    "owner_team": {
        "api team": "api-platform",
        "api-platform-sre": "api-platform",
        "payments": "payments-sre",
        "payments team": "payments-sre",
        "security": "security-response",
        "secops": "security-response",
    },
    "incident_type": {
        "latency": "latency-regression",
        "dependency": "dependency-outage",
        "credential leak": "credential-compromise",
    },
    "first_action": {
        "rollback": "rollback-canary",
        "rollback deploy": "rollback-canary",
        "failover": "failover-region",
        "rotate keys": "revoke-keys",
        "revoke tokens": "revoke-keys",
    },
    "customer_impact": {
        "degraded": "degraded-search",
        "checkout failed": "checkout-failed",
        "data risk": "active-data-risk",
    },
    "escalation_target": {
        "vendor": "cloud-vendor",
        "legal": "legal-compliance",
    },
    "communication_mode": {
        "executive bridge": "exec-bridge",
        "war room": "exec-bridge",
    },
}


@dataclass(frozen=True)
class TaskSpec:
    name: str
    difficulty: DifficultyLevel
    incident_title: str
    incident_summary: str
    scenario_tip: str
    signals: Dict[str, str]
    required_fields: Dict[str, str]
    field_weights: Dict[str, float]
    keyword_targets: List[str]
    keyword_weight: float
    max_steps: int
    allowed_values: Dict[str, List[str]]


TASKS: Dict[str, TaskSpec] = {
    "easy_api_latency_spike": TaskSpec(
        name="easy_api_latency_spike",
        difficulty="easy",
        incident_title="API latency spike after canary release",
        incident_summary=(
            "Search API latency and timeout errors increased immediately after a canary "
            "deployment. You are on call and must classify and route the incident."
        ),
        scenario_tip=(
            "Prioritize restoring latency quickly and classify the issue based on deploy "
            "correlation evidence."
        ),
        signals={
            "signal-1": (
                "Gateway p95 latency increased from 180ms to 2.4s within 7 minutes "
                "of deploying build 2026.04.07-rc3."
            ),
            "signal-2": (
                "Timeout errors on /search rose to 2.1%. Non-search endpoints remain stable."
            ),
            "signal-3": (
                "Rolling back canary to rc2 reduced p95 by 35% in 5 minutes."
            ),
        },
        required_fields={
            "severity": "sev2",
            "owner_team": "api-platform",
            "incident_type": "latency-regression",
            "first_action": "rollback-canary",
            "customer_impact": "degraded-search",
        },
        field_weights={
            "severity": 0.16,
            "owner_team": 0.16,
            "incident_type": 0.20,
            "first_action": 0.20,
            "customer_impact": 0.16,
        },
        keyword_targets=["rollback", "p95 latency", "timeout errors", "canary"],
        keyword_weight=0.12,
        max_steps=10,
        allowed_values={
            "severity": ["sev0", "sev1", "sev2", "sev3"],
            "owner_team": ["api-platform", "payments-sre", "security-response"],
            "incident_type": [
                "latency-regression",
                "dependency-outage",
                "credential-compromise",
            ],
            "first_action": ["rollback-canary", "failover-region", "revoke-keys"],
            "customer_impact": [
                "degraded-search",
                "checkout-failed",
                "active-data-risk",
            ],
        },
    ),
    "medium_payment_processor_outage": TaskSpec(
        name="medium_payment_processor_outage",
        difficulty="medium",
        incident_title="Primary payment processor outage",
        incident_summary=(
            "Checkout failures are climbing due to upstream processor errors. "
            "Agents must route, classify, and define escalation and communication."
        ),
        scenario_tip=(
            "Balance immediate mitigation and external coordination. The right owner, "
            "fallback action, and escalation target are all required for full credit."
        ),
        signals={
            "signal-1": (
                "Checkout failure rate reached 18%. 5xx spikes map to payment authorization."
            ),
            "signal-2": (
                "Primary processor API returns intermittent 503 and timeout responses."
            ),
            "signal-3": (
                "Secondary region failover test restored 72% successful payment auth."
            ),
            "signal-4": (
                "Queue backlog has grown for retries; customer support tickets rising."
            ),
        },
        required_fields={
            "severity": "sev1",
            "owner_team": "payments-sre",
            "incident_type": "dependency-outage",
            "first_action": "failover-region",
            "customer_impact": "checkout-failed",
            "escalation_target": "cloud-vendor",
        },
        field_weights={
            "severity": 0.14,
            "owner_team": 0.14,
            "incident_type": 0.16,
            "first_action": 0.16,
            "customer_impact": 0.16,
            "escalation_target": 0.12,
        },
        keyword_targets=[
            "payment processor",
            "failover",
            "queue backlog",
            "incident channel",
            "eta",
        ],
        keyword_weight=0.12,
        max_steps=12,
        allowed_values={
            "severity": ["sev0", "sev1", "sev2", "sev3"],
            "owner_team": ["api-platform", "payments-sre", "security-response"],
            "incident_type": [
                "latency-regression",
                "dependency-outage",
                "credential-compromise",
            ],
            "first_action": ["rollback-canary", "failover-region", "revoke-keys"],
            "customer_impact": [
                "degraded-search",
                "checkout-failed",
                "active-data-risk",
            ],
            "escalation_target": ["none", "cloud-vendor", "legal-compliance"],
        },
    ),
    "hard_credential_compromise": TaskSpec(
        name="hard_credential_compromise",
        difficulty="hard",
        incident_title="Potential credential compromise with active abuse",
        incident_summary=(
            "An internal token appears leaked and is being used from unknown geographies. "
            "You must contain the blast radius, route correctly, and trigger governance flow."
        ),
        scenario_tip=(
            "Fast containment and compliance escalation are both mandatory. "
            "This task expects explicit executive communication planning."
        ),
        signals={
            "signal-1": (
                "Access logs show a service token used from 4 new regions in under 10 minutes."
            ),
            "signal-2": (
                "Token scope includes read access to customer profile snapshots."
            ),
            "signal-3": (
                "New suspicious API keys were minted from the same principal after anomaly start."
            ),
            "signal-4": (
                "IAM audit indicates the token was exposed via misconfigured CI logs."
            ),
            "signal-5": (
                "Immediate token revocation tests blocked further suspicious requests."
            ),
        },
        required_fields={
            "severity": "sev0",
            "owner_team": "security-response",
            "incident_type": "credential-compromise",
            "first_action": "revoke-keys",
            "customer_impact": "active-data-risk",
            "escalation_target": "legal-compliance",
            "communication_mode": "exec-bridge",
        },
        field_weights={
            "severity": 0.13,
            "owner_team": 0.13,
            "incident_type": 0.14,
            "first_action": 0.14,
            "customer_impact": 0.14,
            "escalation_target": 0.11,
            "communication_mode": 0.09,
        },
        keyword_targets=[
            "key rotation",
            "token revocation",
            "blast radius",
            "forensic timeline",
            "regulator notice",
            "containment",
        ],
        keyword_weight=0.12,
        max_steps=14,
        allowed_values={
            "severity": ["sev0", "sev1", "sev2", "sev3"],
            "owner_team": ["api-platform", "payments-sre", "security-response"],
            "incident_type": [
                "latency-regression",
                "dependency-outage",
                "credential-compromise",
            ],
            "first_action": ["rollback-canary", "failover-region", "revoke-keys"],
            "customer_impact": [
                "degraded-search",
                "checkout-failed",
                "active-data-risk",
            ],
            "escalation_target": ["none", "cloud-vendor", "legal-compliance"],
            "communication_mode": ["incident-channel", "exec-bridge"],
        },
    ),
}


def list_task_names() -> List[str]:
    return list(TASKS.keys())


def get_task(task_name: str) -> TaskSpec:
    if task_name not in TASKS:
        supported = ", ".join(list_task_names())
        raise ValueError(f"Unknown task '{task_name}'. Supported tasks: {supported}")
    return TASKS[task_name]


def normalize_value(field: str, value: str | None) -> str:
    if value is None:
        return ""
    normalized = str(value).strip().lower().replace("_", "-")
    if not normalized:
        return ""
    return VALUE_ALIASES.get(field, {}).get(normalized, normalized)


def _grade_severity(expected: str, actual: str) -> float:
    if actual == expected:
        return 1.0
    if actual not in SEVERITY_ORDER or expected not in SEVERITY_ORDER:
        return 0.0
    expected_idx = SEVERITY_ORDER.index(expected)
    actual_idx = SEVERITY_ORDER.index(actual)
    delta = abs(expected_idx - actual_idx)
    if delta == 1:
        return 0.5
    if delta == 2:
        return 0.2
    return 0.0


def _grade_field(field: str, expected: str, actual: str) -> float:
    if actual == expected:
        return 1.0
    if field == "severity":
        return _grade_severity(expected, actual)
    if not actual:
        return 0.0
    if field in {"owner_team", "incident_type", "first_action"}:
        expected_tokens = set(expected.split("-"))
        actual_tokens = set(actual.split("-"))
        overlap = len(expected_tokens.intersection(actual_tokens))
        return 0.4 if overlap >= max(1, len(expected_tokens) - 1) else 0.0
    return 0.0


def _keyword_score(note: str, keyword_targets: List[str]) -> float:
    if not keyword_targets:
        return 1.0
    normalized_note = note.lower()
    hits = sum(1 for keyword in keyword_targets if keyword in normalized_note)
    return hits / len(keyword_targets)


def evaluate_submission(
    task: TaskSpec, decisions: Dict[str, str], note: str
) -> Dict[str, float | Dict[str, float]]:
    field_scores: Dict[str, float] = {}
    weighted_sum = 0.0
    for field, expected in task.required_fields.items():
        actual = normalize_value(field, decisions.get(field))
        score = _grade_field(field, expected, actual)
        field_scores[field] = score
        weighted_sum += score * task.field_weights.get(field, 0.0)

    note_score = _keyword_score(note, task.keyword_targets)
    total_score = weighted_sum + task.keyword_weight * note_score
    total_score = min(1.0, max(0.0, total_score))
    return {
        "score": total_score,
        "note_score": note_score,
        "field_scores": field_scores,
    }


def success_threshold_for(difficulty: DifficultyLevel) -> float:
    if difficulty == "easy":
        return 0.85
    if difficulty == "medium":
        return 0.8
    return 0.75
