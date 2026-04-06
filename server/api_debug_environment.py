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
MOCK_BASE = "http://localhost:7860"


class APIDebugEnvironment(Environment):

    def __init__(self):
        self._state = APIState(episode_id="init", step_count=0, task_id="easy", max_steps=5, solved=False)
        self._current_task = None

    def reset(self, task_id: str = "easy", **kwargs) -> APIObservation:
        # Reset the mock API state to ensure strict episode isolation
        try:
            with httpx.Client(base_url=MOCK_BASE, timeout=2.0) as http:
                http.post("/mock_api/_admin/reset")
        except Exception:
            pass

        if task_id not in TASK_REGISTRY:
            task_id = "easy"
        self._current_task = random.choice(TASK_REGISTRY[task_id])
        self._state = APIState(
            episode_id=f"ep_{random.randint(10000, 99999)}",
            step_count=0,
            task_id=task_id,
            max_steps=10,
            solved=False,
        )
        return APIObservation(
            task_id=task_id,
            task_description=self._current_task["description"],
            broken_request=self._current_task["broken_request"],
            last_status_code=0,
            last_response_headers={},
            last_response_body="",
            step_feedback="Episode started. Read the task description and fix the broken request.",
            current_score=0.0,
            attempt=0,
            reward=0.0,
            done=False,
        )

    def step(self, action: APIAction, **kwargs) -> APIObservation:
        if self._current_task is None:
            self.reset(task_id="easy")

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
            resp_body = resp.text
        except Exception as e:
            status = 0
            resp_headers = {}
            resp_body = f"Request error: {str(e)}"

        reward = GRADER.grade(
            response_status=status,
            response_body=resp_body,
            expected_status=task["expected_status"],
            expected_schema=task["expected_schema"],
            attempt=self._state.step_count,
            max_steps=self._state.max_steps,
        )

        feedback = GRADER.get_feedback(status, task["expected_status"])
        solved = status == task["expected_status"] and reward >= 0.8
        self._state.solved = solved
        done = solved or self._state.step_count >= self._state.max_steps

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
        )

    @property
    def state(self) -> APIState:
        return self._state