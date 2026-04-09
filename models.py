from typing import Dict, List, Literal, Optional

from openenv.core.env_server.types import Action, Observation, State
from pydantic import Field


CommandName = Literal[
    "view_brief",
    "view_signal",
    "set_field",
    "append_note",
    "submit",
]

DifficultyLevel = Literal["easy", "medium", "hard"]


class ReliabilityTriageAction(Action):
    command: CommandName = Field(..., description="Action to execute")
    field: Optional[str] = Field(default=None, description="Decision field name")
    value: Optional[str] = Field(default=None, description="Decision field value")
    signal_id: Optional[str] = Field(default=None, description="Signal identifier")
    note: Optional[str] = Field(default=None, description="Incident note content")


class ReliabilityTriageObservation(Observation):
    task_name: str = Field(default="", description="Active task identifier")
    difficulty: DifficultyLevel = Field(default="easy", description="Task difficulty")
    incident_title: str = Field(default="", description="Incident headline")
    incident_summary: str = Field(default="", description="Scenario summary")
    visible_signals: List[str] = Field(
        default_factory=list, description="Signals opened by the agent"
    )
    available_fields: List[str] = Field(
        default_factory=list, description="Decision fields to submit"
    )
    decisions: Dict[str, str] = Field(
        default_factory=dict, description="Current normalized decisions"
    )
    note: str = Field(default="", description="Current triage note")
    checklist_progress: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Current normalized score estimate"
    )
    remaining_steps: int = Field(default=0, ge=0, description="Remaining step budget")
    last_feedback: str = Field(default="", description="Feedback for the last action")


class ReliabilityTriageState(State):
    task_name: str = Field(default="", description="Task identifier")
    difficulty: DifficultyLevel = Field(default="easy", description="Task difficulty")
    max_steps: int = Field(default=0, ge=1, description="Episode step cap")
    submitted: bool = Field(default=False, description="Submit action has been called")
    score: float = Field(default=0.0, ge=0.0, le=1.0, description="Current score")
    invalid_actions: int = Field(default=0, ge=0, description="Invalid action count")
