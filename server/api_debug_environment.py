import os
import random
import httpx

try:
    from openenv.core.env_server import Environment
except ImportError:
    from openenv.core.env_server.interfaces import Environment

from models import APIAction, APIObservation, APIState
from tasks.registry import TASK_REGISTRY
from graders.grader import APIGrader

GRADER = APIGrader()
MOCK_BASE = os.getenv("MOCK_BASE_URL", "http://localhost:7860")
MAX_RESPONSE_BODY_LENGTH = 2000


class APIDebugEnvironment(Environment):

    def __init__(self):
        self._state = APIState(episode_id="init", step_count=0, task_id="easy", max_steps=10, solved=False, current_step_index=0, curriculum_level=0)
        self._current_task = None

    def reset(self, task_id: str = "auto", **kwargs) -> APIObservation:
        import copy
        import uuid

        old_level = getattr(self._state, "curriculum_level", 0)
        if getattr(self._state, "solved", False):
            old_level += 1

        effective_task_id = task_id
        if task_id == "auto":
            levels = ["easy", "medium", "hard", "expert"]
            effective_task_id = levels[min(old_level, len(levels) - 1)]

        if effective_task_id not in TASK_REGISTRY:
            effective_task_id = "easy"
            
        task = copy.deepcopy(random.choice(TASK_REGISTRY[effective_task_id]))

        dyn_config = {
            "demo_token": f"tok_{uuid.uuid4().hex[:8]}",
            "client_id": f"cli_{uuid.uuid4().hex[:8]}",
            "client_secret": f"sec_{uuid.uuid4().hex[:8]}"
        }

        try:
            with httpx.Client(base_url=MOCK_BASE, timeout=2.0) as http:
                http.post("/mock_api/_admin/reset", json=dyn_config)
        except Exception:
            pass

        try:
            task["description"] = task["description"].format(**dyn_config)
            req = task["broken_request"]
            if "headers" in req:
                req["headers"] = {k: (v.format(**dyn_config) if isinstance(v, str) else v) for k, v in req["headers"].items()}
        except Exception:
            pass

        self._current_task = task
        max_steps = self._current_task.get("max_steps", 10)
        
        self._state = APIState(
            episode_id=f"ep_{random.randint(10000, 99999)}",
            step_count=0,
            task_id=task_id,
            max_steps=max_steps,
            solved=False,
            current_step_index=0,
            visited_endpoints=set(),
            curriculum_level=old_level
        )
        return APIObservation(
            task_id=task_id,
            task_description=self._current_task["description"],
            broken_request=self._current_task["broken_request"],
            last_status_code=0,
            last_response_headers={},
            last_response_body="",
            step_feedback="Episode started. Read the task description and fix the broken request.",
            current_score=0.001,
            attempt=0,
            reward=0.001,
            done=False,
            current_step_index=0
        )

    def step(self, action: APIAction, **kwargs) -> APIObservation:
        if self._current_task is None:
            self.reset(task_id="auto")

        self._state.step_count += 1
        task = self._current_task

        try:
            with httpx.Client(base_url=MOCK_BASE, timeout=5.0) as http:
                resp = http.request(
                    method=action.method.upper(),
                    url=action.url,
                    headers=action.headers,
                    json=action.body if action.body else None,
                    params=action.query_params,
                )
            status = resp.status_code
            resp_headers = dict(resp.headers)
            resp_body = resp.text[:MAX_RESPONSE_BODY_LENGTH]
        except Exception as e:
            status = 0
            resp_headers = {}
            resp_body = f"Request error: {str(e)}"

        expected_schema = task["expected_schema"]
        expected_status = task["expected_status"]
        is_chain = isinstance(expected_schema, list)

        target_schema = expected_schema[self._state.current_step_index] if is_chain else expected_schema
        target_status = expected_status[self._state.current_step_index] if isinstance(expected_status, list) else expected_status

        reward = GRADER.grade(
            response_status=status,
            response_body=resp_body,
            expected_status=target_status,
            expected_schema=target_schema,
            attempt=self._state.step_count,
            max_steps=self._state.max_steps,
        )

        feedback = GRADER.get_feedback(status, target_status)
        step_solved = status == target_status and reward >= 0.8
        
        if is_chain and step_solved:
            self._state.current_step_index += 1
            if self._state.current_step_index >= len(expected_schema):
                self._state.solved = True
                feedback += " Chain completed successfully!"
            else:
                feedback += f" Step {self._state.current_step_index} complete. Moving to next step."
                reward = 0.5  # Partial reward for finishing a step
        else:
            self._state.solved = step_solved if not is_chain else False

        if action.url not in self._state.visited_endpoints and status > 0 and status < 500:
            self._state.visited_endpoints.add(action.url)
            reward += 0.05
        reward = round(min(0.999, max(0.001, reward)), 4)

        done = self._state.solved or self._state.step_count >= self._state.max_steps

        return APIObservation(
            task_id=self._state.task_id,
            task_description=task["description"],
            broken_request=task["broken_request"],
            last_status_code=status,
            last_response_headers=resp_headers,
            last_response_body=resp_body,
            step_feedback=feedback,
            current_score=reward,
            attempt=self._state.step_count,
            reward=reward,
            done=done,
            current_step_index=self._state.current_step_index
        )

    @property
    def state(self) -> APIState:
        return self._state
