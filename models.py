from __future__ import annotations

try:
    from openenv.core.env_server.types import Action, Observation, State
except ImportError:
    try:
        from openenv.core.models import Action, Observation, State
    except ImportError:
        from openenv.core.env_server import Action, Observation, State

from typing import Set
from pydantic import Field


class APIAction(Action):
    method: str = Field(default="GET")
    url: str = Field(default="/mock_api/users")
    headers: dict = Field(default_factory=dict)
    body: dict = Field(default_factory=dict)
    query_params: dict = Field(default_factory=dict)


class APIObservation(Observation):
    task_id: str = Field(default="easy")
    task_description: str = Field(default="")
    broken_request: dict = Field(default_factory=dict)
    last_status_code: int = Field(default=0)
    last_response_headers: dict = Field(default_factory=dict)
    last_response_body: str = Field(default="")
    step_feedback: str = Field(default="")
    current_score: float = Field(default=0.0)
    attempt: int = Field(default=0)
    reward: float = Field(default=0.0)
    done: bool = Field(default=False)
    current_step_index: int = Field(default=0)


class APIState(State):
    task_id: str = Field(default="easy")
    max_steps: int = Field(default=10)
    solved: bool = Field(default=False)
    current_step_index: int = Field(default=0)
    visited_endpoints: Set[str] = Field(default_factory=set)
    curriculum_level: int = Field(default=0)
