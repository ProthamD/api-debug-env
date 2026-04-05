from openenv.core.env_server import Environment
try:
    from openenv.core.env_server.types import Action, Observation, State
except ImportError:
    from openenv.core.models import Action, Observation, State
from pydantic import Field
from typing import Optional


class APIAction(Action):
    method: str = Field(default="GET")
    url: str = Field(default="/mock_api/users")
    headers: dict = Field(default_factory=dict)
    body: Optional[dict] = Field(default=None)
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


class APIState(State):
    task_id: str = Field(default="easy")
    max_steps: int = Field(default=5)
    solved: bool = Field(default=False)
