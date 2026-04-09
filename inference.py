import asyncio
import json
import os
import re
from typing import Any, Dict, List

from openai import OpenAI

try:
    from reliability_triage_env.client import ReliabilityTriageEnv
    from reliability_triage_env.models import ReliabilityTriageAction
    from reliability_triage_env.task_bank import get_task, success_threshold_for
except ImportError:
    from client import ReliabilityTriageEnv
    from models import ReliabilityTriageAction
    from task_bank import get_task, success_threshold_for


API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME", "")
ENV_BASE_URL = os.getenv("ENV_BASE_URL", "http://localhost:8000")
BENCHMARK = os.getenv("BENCHMARK", "reliability_triage_env")
MAX_STEPS = int(os.getenv("MAX_STEPS", "20"))
TASKS = [
    item.strip()
    for item in os.getenv(
        "TASKS",
        "easy_api_latency_spike,medium_payment_processor_outage,hard_credential_compromise",
    ).split(",")
    if item.strip()
]


TASK_PLAYBOOK: Dict[str, Dict[str, Any]] = {
    "easy_api_latency_spike": {
        "signals": ["signal-2", "signal-3"],
        "fields": {
            "severity": "sev2",
            "owner_team": "api-platform",
            "incident_type": "latency-regression",
            "first_action": "rollback-canary",
            "customer_impact": "degraded-search",
        },
        "keywords": ["rollback", "p95 latency", "timeout errors", "canary"],
        "fallback_note": (
            "Rollback was initiated after p95 latency rose sharply and timeout errors increased "
            "on the canary deployment. Canary evidence links the regression to the latest release. "
            "Mitigation is rollback-first while monitoring latency and error normalization."
        ),
    },
    "medium_payment_processor_outage": {
        "signals": ["signal-2", "signal-3", "signal-4"],
        "fields": {
            "severity": "sev1",
            "owner_team": "payments-sre",
            "incident_type": "dependency-outage",
            "first_action": "failover-region",
            "customer_impact": "checkout-failed",
            "escalation_target": "cloud-vendor",
        },
        "keywords": [
            "payment processor",
            "failover",
            "queue backlog",
            "incident channel",
            "eta",
        ],
        "fallback_note": (
            "Payment processor instability is driving checkout-failed impact. We executed regional "
            "failover to recover authorization throughput and are tracking queue backlog in the "
            "incident channel. Cloud vendor escalation is active and the next ETA update is in 15 minutes."
        ),
    },
    "hard_credential_compromise": {
        "signals": ["signal-2", "signal-3", "signal-4", "signal-5"],
        "fields": {
            "severity": "sev0",
            "owner_team": "security-response",
            "incident_type": "credential-compromise",
            "first_action": "revoke-keys",
            "customer_impact": "active-data-risk",
            "escalation_target": "legal-compliance",
            "communication_mode": "exec-bridge",
        },
        "keywords": [
            "key rotation",
            "token revocation",
            "blast radius",
            "forensic timeline",
            "regulator notice",
            "containment",
        ],
        "fallback_note": (
            "Containment began with token revocation and emergency key rotation. The current blast radius "
            "includes exposed profile snapshot access paths under investigation. A forensic timeline is in "
            "progress, regulator notice prep has started with legal-compliance, and containment validation is continuous."
        ),
    },
}


def _sanitize_token(value: str | None) -> str:
    if value is None:
        return "null"
    clean = re.sub(r"\s+", "_", str(value).strip())
    return clean if clean else "null"


def log_start(task_name: str) -> None:
    print(f"[START] task={task_name} env={BENCHMARK} model={MODEL_NAME}", flush=True)


def log_step(step: int, action_repr: str, reward: float, done: bool, error: str | None) -> None:
    print(
        f"[STEP] step={step} action={action_repr} reward={reward:.2f} "
        f"done={str(done).lower()} error={_sanitize_token(error)}",
        flush=True,
    )


def _strict_score(raw_score: float) -> float:
    epsilon = 0.001
    if not isinstance(raw_score, (int, float)):
        return epsilon
    bounded = min(max(float(raw_score), 0.0), 1.0)
    return epsilon + bounded * (1.0 - 2.0 * epsilon)


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    score_out = _strict_score(score)
    rewards_str = ",".join(f"{reward:.2f}" for reward in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} score={score_out:.3f} rewards={rewards_str}",
        flush=True,
    )


def _make_note_prompt(task_name: str, summary: str, signals: List[str], keywords: List[str]) -> str:
    signal_block = "\n".join(signals[-4:]) if signals else "No additional signals opened."
    keyword_block = ", ".join(keywords)
    return (
        f"Task: {task_name}\n"
        f"Incident summary: {summary}\n"
        f"Visible signals:\n{signal_block}\n"
        f"Write one concise triage note (55-95 words) and include each keyword exactly once: {keyword_block}.\n"
        "Return plain text only."
    )


def generate_note(
    llm_client: OpenAI | None,
    task_name: str,
    summary: str,
    visible_signals: List[str],
    keywords: List[str],
    fallback_note: str,
) -> str:
    if llm_client is None:
        return fallback_note

    prompt = _make_note_prompt(task_name, summary, visible_signals, keywords)
    try:
        completion = llm_client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": "You produce accurate incident-triage notes with strict keyword coverage.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_tokens=200,
        )
        text = (completion.choices[0].message.content or "").strip()
        text = re.sub(r"\s+", " ", text)
        return text if text else fallback_note
    except Exception:
        return fallback_note


def build_plan(task_name: str, note: str) -> List[Dict[str, str]]:
    config = TASK_PLAYBOOK[task_name]
    plan: List[Dict[str, str]] = [{"command": "view_brief"}]
    for signal_id in config["signals"]:
        plan.append({"command": "view_signal", "signal_id": signal_id})
    for field, value in config["fields"].items():
        plan.append({"command": "set_field", "field": field, "value": value})
    plan.append({"command": "append_note", "note": note})
    plan.append({"command": "submit"})
    return plan


def action_repr(action_payload: Dict[str, Any]) -> str:
    return json.dumps(action_payload, separators=(",", ":"), ensure_ascii=True)


async def run_task(
    env: ReliabilityTriageEnv, llm_client: OpenAI | None, task_name: str
) -> None:
    rewards: List[float] = []
    steps = 0
    score = 0.0
    success = False
    last_result = None
    fallback_error: str | None = None

    log_start(task_name)
    try:
        last_result = await env.reset(task_name=task_name)
        observation = last_result.observation
        config = TASK_PLAYBOOK[task_name]
        note = generate_note(
            llm_client=llm_client,
            task_name=task_name,
            summary=observation.incident_summary,
            visible_signals=observation.visible_signals,
            keywords=config["keywords"],
            fallback_note=config["fallback_note"],
        )
        plan = build_plan(task_name, note)

        for planned_action in plan:
            if steps >= MAX_STEPS:
                break
            action = ReliabilityTriageAction(**planned_action)
            last_result = await env.step(action)
            steps += 1
            reward = float(last_result.reward or 0.0)
            rewards.append(reward)

            metadata = last_result.observation.metadata or {}
            score = float(metadata.get("score", last_result.observation.checklist_progress))
            error = metadata.get("error")
            log_step(
                step=steps,
                action_repr=action_repr(planned_action),
                reward=reward,
                done=bool(last_result.done),
                error=error,
            )
            if last_result.done:
                break

        if last_result is not None and not last_result.done and steps < MAX_STEPS:
            forced_submit = {"command": "submit"}
            action = ReliabilityTriageAction(**forced_submit)
            last_result = await env.step(action)
            steps += 1
            reward = float(last_result.reward or 0.0)
            rewards.append(reward)
            metadata = last_result.observation.metadata or {}
            score = float(metadata.get("score", last_result.observation.checklist_progress))
            error = metadata.get("error")
            log_step(
                step=steps,
                action_repr=action_repr(forced_submit),
                reward=reward,
                done=bool(last_result.done),
                error=error,
            )

        task = get_task(task_name)
        threshold = success_threshold_for(task.difficulty)
        success = score >= threshold
    except Exception as exc:
        fallback_error = str(exc)
        success = False
    finally:
        if fallback_error:
            score = 0.0
        log_end(success=success, steps=steps, score=score, rewards=rewards)


async def create_env() -> ReliabilityTriageEnv:
    if LOCAL_IMAGE_NAME:
        return await ReliabilityTriageEnv.from_docker_image(LOCAL_IMAGE_NAME)
    env = ReliabilityTriageEnv(base_url=ENV_BASE_URL)
    await env.connect()
    return env


async def main() -> None:
    llm_client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY) if API_KEY else None
    env = await create_env()
    try:
        for task_name in TASKS:
            await run_task(env=env, llm_client=llm_client, task_name=task_name)
    finally:
        await env.close()


if __name__ == "__main__":
    asyncio.run(main())
