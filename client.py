from typing import Any, Dict

from openenv.core import EnvClient
from openenv.core.client_types import StepResult

try:
    from .models import (
        ReliabilityTriageAction,
        ReliabilityTriageObservation,
        ReliabilityTriageState,
    )
except ImportError:
    from models import (  # type: ignore
        ReliabilityTriageAction,
        ReliabilityTriageObservation,
        ReliabilityTriageState,
    )


class ReliabilityTriageEnv(
    EnvClient[
        ReliabilityTriageAction,
        ReliabilityTriageObservation,
        ReliabilityTriageState,
    ]
):
    def _step_payload(self, action: ReliabilityTriageAction) -> Dict[str, Any]:
        return action.model_dump(exclude_none=True)

    def _parse_result(self, payload: Dict[str, Any]) -> StepResult[ReliabilityTriageObservation]:
        observation_payload = payload.get("observation", {})
        observation = ReliabilityTriageObservation(
            task_name=observation_payload.get("task_name", ""),
            difficulty=observation_payload.get("difficulty", "easy"),
            incident_title=observation_payload.get("incident_title", ""),
            incident_summary=observation_payload.get("incident_summary", ""),
            visible_signals=observation_payload.get("visible_signals", []),
            available_fields=observation_payload.get("available_fields", []),
            decisions=observation_payload.get("decisions", {}),
            note=observation_payload.get("note", ""),
            checklist_progress=observation_payload.get("checklist_progress", 0.0),
            remaining_steps=observation_payload.get("remaining_steps", 0),
            last_feedback=observation_payload.get("last_feedback", ""),
            done=payload.get("done", False),
            reward=payload.get("reward"),
            metadata=observation_payload.get("metadata", {}),
        )
        return StepResult(
            observation=observation,
            reward=payload.get("reward"),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: Dict[str, Any]) -> ReliabilityTriageState:
        return ReliabilityTriageState(
            episode_id=payload.get("episode_id"),
            step_count=payload.get("step_count", 0),
            task_name=payload.get("task_name", ""),
            difficulty=payload.get("difficulty", "easy"),
            max_steps=payload.get("max_steps", 1),
            submitted=payload.get("submitted", False),
            score=payload.get("score", 0.0),
            invalid_actions=payload.get("invalid_actions", 0),
        )
