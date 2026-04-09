from __future__ import annotations

from typing import Dict, Set
from uuid import uuid4

from openenv.core.env_server.interfaces import Environment

try:
    from ..models import (
        ReliabilityTriageAction,
        ReliabilityTriageObservation,
        ReliabilityTriageState,
    )
    from ..task_bank import (
        TaskSpec,
        evaluate_submission,
        get_task,
        list_task_names,
        normalize_value,
        success_threshold_for,
    )
except ImportError:
    from models import (
        ReliabilityTriageAction,
        ReliabilityTriageObservation,
        ReliabilityTriageState,
    )
    from task_bank import (
        TaskSpec,
        evaluate_submission,
        get_task,
        list_task_names,
        normalize_value,
        success_threshold_for,
    )


class ReliabilityTriageEnvironment(
    Environment[
        ReliabilityTriageAction,
        ReliabilityTriageObservation,
        ReliabilityTriageState,
    ]
):
    SUPPORTS_CONCURRENT_SESSIONS = True

    def __init__(self) -> None:
        super().__init__()
        self._task: TaskSpec = get_task(list_task_names()[0])
        self._decisions: Dict[str, str] = {}
        self._note = ""
        self._opened_signals: Set[str] = set()
        self._brief_viewed = False
        self._last_action_fingerprint = ""
        self._last_feedback = ""
        self._score = 0.0
        self._invalid_actions = 0
        self._state = ReliabilityTriageState(
            episode_id=str(uuid4()),
            step_count=0,
            task_name=self._task.name,
            difficulty=self._task.difficulty,
            max_steps=self._task.max_steps,
            submitted=False,
            score=0.0,
            invalid_actions=0,
        )

    def reset(
        self,
        seed: int | None = None,
        episode_id: str | None = None,
        **kwargs,
    ) -> ReliabilityTriageObservation:
        del seed
        task_name = str(kwargs.get("task_name", list_task_names()[0]))
        self._task = get_task(task_name)
        self._decisions = {}
        self._note = ""
        self._opened_signals = {"signal-1"}
        self._brief_viewed = False
        self._last_action_fingerprint = ""
        self._last_feedback = "Episode started. Open signals, set fields, then submit."
        self._score = 0.0
        self._invalid_actions = 0
        self._state = ReliabilityTriageState(
            episode_id=episode_id or str(uuid4()),
            step_count=0,
            task_name=self._task.name,
            difficulty=self._task.difficulty,
            max_steps=self._task.max_steps,
            submitted=False,
            score=0.0,
            invalid_actions=0,
        )
        return self._build_observation(reward=0.0, done=False)

    def step(
        self,
        action: ReliabilityTriageAction,
        timeout_s: float | None = None,
        **kwargs,
    ) -> ReliabilityTriageObservation:
        del timeout_s
        del kwargs

        if self._state.submitted:
            self._last_feedback = "Episode already submitted. Reset to start a new task."
            return self._build_observation(reward=0.0, done=True)

        self._state.step_count += 1
        reward = -0.01
        error: str | None = None
        command = action.command

        fingerprint = self._fingerprint(action)
        if fingerprint == self._last_action_fingerprint:
            reward -= 0.03
        self._last_action_fingerprint = fingerprint

        previous_score = self._score
        if command == "view_brief":
            reward += self._handle_view_brief()
        elif command == "view_signal":
            reward, error = self._handle_view_signal(action, reward)
        elif command == "set_field":
            reward, error = self._handle_set_field(action, reward)
        elif command == "append_note":
            reward, error = self._handle_append_note(action, reward)
        elif command == "submit":
            reward += self._handle_submit()
        else:
            error = f"Unsupported command: {command}"
            reward -= 0.15

        if error:
            self._invalid_actions += 1
            self._state.invalid_actions = self._invalid_actions
            self._last_feedback = error

        new_breakdown = evaluate_submission(self._task, self._decisions, self._note)
        self._score = float(new_breakdown["score"])
        self._state.score = self._score
        if command != "submit":
            reward += max(0.0, self._score - previous_score) * 0.8

        done = self._state.submitted
        if not done and self._state.step_count >= self._task.max_steps:
            done = True
            self._state.submitted = True
            self._last_feedback = (
                f"Step budget reached ({self._task.max_steps}). Episode auto-closed."
            )

        reward = min(1.0, max(-1.0, reward))
        return self._build_observation(reward=reward, done=done, error=error)

    @property
    def state(self) -> ReliabilityTriageState:
        return self._state

    def _handle_view_brief(self) -> float:
        if self._brief_viewed:
            self._last_feedback = "Brief already reviewed."
            return -0.01
        self._brief_viewed = True
        self._last_feedback = "Brief opened. Inspect additional signals for evidence."
        return 0.02

    def _handle_view_signal(
        self, action: ReliabilityTriageAction, base_reward: float
    ) -> tuple[float, str | None]:
        signal_id = (action.signal_id or "").strip().lower()
        if not signal_id:
            return base_reward - 0.12, "view_signal requires signal_id."
        if signal_id not in self._task.signals:
            return base_reward - 0.12, f"Unknown signal_id '{signal_id}'."
        if signal_id in self._opened_signals:
            self._last_feedback = f"{signal_id} already visible."
            return base_reward - 0.01, None
        self._opened_signals.add(signal_id)
        self._last_feedback = f"{signal_id} opened."
        return base_reward + 0.03, None

    def _handle_set_field(
        self, action: ReliabilityTriageAction, base_reward: float
    ) -> tuple[float, str | None]:
        field = (action.field or "").strip().lower()
        if not field:
            return base_reward - 0.12, "set_field requires field."
        if field not in self._task.required_fields:
            return (
                base_reward - 0.12,
                f"Field '{field}' is not required for this task.",
            )
        if action.value is None or str(action.value).strip() == "":
            return base_reward - 0.12, "set_field requires non-empty value."
        normalized = normalize_value(field, str(action.value))
        self._decisions[field] = normalized
        expected = self._task.required_fields[field]
        if normalized == expected:
            self._last_feedback = f"{field} set correctly."
            return base_reward + 0.03, None
        self._last_feedback = f"{field} set, but does not match the expected incident triage."
        return base_reward - 0.02, None

    def _handle_append_note(
        self, action: ReliabilityTriageAction, base_reward: float
    ) -> tuple[float, str | None]:
        note = (action.note or "").strip()
        if not note:
            return base_reward - 0.12, "append_note requires note content."
        previous_breakdown = evaluate_submission(self._task, self._decisions, self._note)
        self._note = note
        new_breakdown = evaluate_submission(self._task, self._decisions, self._note)
        note_gain = float(new_breakdown["note_score"]) - float(previous_breakdown["note_score"])
        if len(note) < 40:
            self._last_feedback = "Note is short; include concrete evidence and mitigation."
            return base_reward - 0.02, None
        self._last_feedback = "Note updated."
        return base_reward + max(0.0, note_gain) * 0.25, None

    def _handle_submit(self) -> float:
        self._state.submitted = True
        threshold = success_threshold_for(self._task.difficulty)
        if self._score >= threshold:
            self._last_feedback = (
                f"Submitted. Task solved above threshold ({threshold:.2f})."
            )
        else:
            self._last_feedback = (
                f"Submitted. Score below threshold ({threshold:.2f}); review evidence alignment."
            )
        return max(0.0, self._score) * 0.2

    def _fingerprint(self, action: ReliabilityTriageAction) -> str:
        return (
            f"{action.command}|{(action.field or '').strip().lower()}|"
            f"{(action.value or '').strip().lower()}|"
            f"{(action.signal_id or '').strip().lower()}|"
            f"{(action.note or '').strip().lower()}"
        )

    def _build_observation(
        self, reward: float, done: bool, error: str | None = None
    ) -> ReliabilityTriageObservation:
        signal_lines = [
            f"{signal_id}: {self._task.signals[signal_id]}"
            for signal_id in sorted(self._opened_signals)
            if signal_id in self._task.signals
        ]
        metadata = {
            "score": round(self._score, 4),
            "task_name": self._task.name,
            "difficulty": self._task.difficulty,
            "invalid_actions": self._invalid_actions,
            "threshold": success_threshold_for(self._task.difficulty),
        }
        if error:
            metadata["error"] = error

        return ReliabilityTriageObservation(
            task_name=self._task.name,
            difficulty=self._task.difficulty,
            incident_title=self._task.incident_title,
            incident_summary=self._task.incident_summary,
            visible_signals=signal_lines,
            available_fields=list(self._task.required_fields.keys()),
            decisions=dict(self._decisions),
            note=self._note,
            checklist_progress=round(self._score, 4),
            remaining_steps=max(0, self._task.max_steps - self._state.step_count),
            last_feedback=self._last_feedback,
            done=done,
            reward=reward,
            metadata=metadata,
        )
