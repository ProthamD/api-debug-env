"""
Tests for API Debug Environment
================================
Covers:
  1. Grader unit tests (grade + _schema_match + get_feedback)
  2. Task registry validation (all tasks have required keys)
  3. Mocked episode lifecycle (reset → step → done)

Run with:
    pytest tests/ -v
"""

import json
import sys
import os
from unittest.mock import MagicMock, patch

# Ensure project root is on sys.path so imports resolve without installation
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest


# ---------------------------------------------------------------------------
# 1. Grader unit tests
# ---------------------------------------------------------------------------

class TestAPIGrader:
    """Unit tests for APIGrader.grade(), ._schema_match(), .get_feedback()."""

    @pytest.fixture(autouse=True)
    def grader(self):
        from graders.grader import APIGrader
        self.g = APIGrader()

    # --- _schema_match ---

    def test_schema_match_empty_schema_returns_1(self):
        assert self.g._schema_match({"foo": "bar"}, {}) == 1.0

    def test_schema_match_full_match(self):
        body   = {"id": 1, "name": "test", "active": True}
        schema = {"id": 0,  "name": ""}
        assert self.g._schema_match(body, schema) == 1.0

    def test_schema_match_partial_match(self):
        body   = {"id": 1, "name": "test"}
        schema = {"id": 0, "name": "", "missing_key": "x"}
        score  = self.g._schema_match(body, schema)
        # 2 out of 3 keys match
        assert abs(score - 2/3) < 1e-9

    def test_schema_match_type_mismatch(self):
        body   = {"id": "string_not_int"}
        schema = {"id": 0}
        assert self.g._schema_match(body, schema) == 0.0

    # --- grade ---

    def test_grade_wrong_status_returns_partial(self):
        score = self.g.grade(
            response_status=404, response_body="not found",
            expected_status=200, expected_schema={"id": 0},
            attempt=1, max_steps=5,
        )
        assert 0.001 <= score <= 0.999
        assert score < 0.5   # should be a small partial score

    def test_grade_correct_status_non_json_body(self):
        score = self.g.grade(
            response_status=200, response_body="not json!",
            expected_status=200, expected_schema={"id": 0},
            attempt=1, max_steps=5,
        )
        assert score == 0.25

    def test_grade_correct_status_perfect_schema(self):
        body_dict = {"id": 1, "name": "alice"}
        score = self.g.grade(
            response_status=200,
            response_body=json.dumps(body_dict),
            expected_status=200,
            expected_schema={"id": 0, "name": ""},
            attempt=1, max_steps=5,
        )
        assert score >= 0.8

    def test_grade_score_clamped(self):
        # Even with a perfect response the score must be < 1.0
        body_dict = {"status": "ok"}
        score = self.g.grade(
            response_status=200,
            response_body=json.dumps(body_dict),
            expected_status=200,
            expected_schema={"status": ""},
            attempt=1, max_steps=5,
        )
        assert 0.001 <= score <= 0.999

    # --- get_feedback ---

    def test_feedback_correct_status(self):
        msg = self.g.get_feedback(200, 200)
        assert "Correct" in msg

    def test_feedback_401(self):
        msg = self.g.get_feedback(401, 200)
        assert "auth" in msg.lower() or "401" in msg

    def test_feedback_unknown_status(self):
        msg = self.g.get_feedback(418, 200)
        assert "418" in msg


# ---------------------------------------------------------------------------
# 2. Task registry validation
# ---------------------------------------------------------------------------

class TestTaskRegistry:
    """Validates that every task in the registry has the required keys."""

    REQUIRED_KEYS = {
        "id", "description", "broken_request",
        "expected_status", "expected_schema", "max_steps",
    }

    REQUIRED_REQUEST_KEYS = {"method", "url", "headers", "body", "query_params"}

    @pytest.fixture(autouse=True)
    def registry(self):
        from tasks.registry import TASK_REGISTRY
        self.registry = TASK_REGISTRY

    def test_all_difficulty_levels_present(self):
        for level in ("easy", "medium", "hard", "expert"):
            assert level in self.registry, f"Missing difficulty level: {level}"

    def test_each_difficulty_has_at_least_one_task(self):
        for level, tasks in self.registry.items():
            assert len(tasks) >= 1, f"No tasks defined for level: {level}"

    def test_all_tasks_have_required_keys(self):
        for level, tasks in self.registry.items():
            for task in tasks:
                missing = self.REQUIRED_KEYS - set(task.keys())
                assert not missing, (
                    f"Task '{task.get('id', '?')}' in '{level}' is missing keys: {missing}"
                )

    def test_broken_request_has_required_keys(self):
        for level, tasks in self.registry.items():
            for task in tasks:
                req     = task["broken_request"]
                missing = self.REQUIRED_REQUEST_KEYS - set(req.keys())
                assert not missing, (
                    f"Task '{task.get('id', '?')}' broken_request missing: {missing}"
                )

    def test_no_format_placeholder_keys_in_body(self):
        """Ensure no task body contains un-formatted {placeholder} as dict keys."""
        for level, tasks in self.registry.items():
            for task in tasks:
                body = task["broken_request"].get("body") or {}
                for key in body:
                    assert not (key.startswith("{") and key.endswith("}")), (
                        f"Task '{task.get('id', '?')}' has placeholder key in body: {key!r}"
                    )

    def test_max_steps_positive_int(self):
        for level, tasks in self.registry.items():
            for task in tasks:
                assert isinstance(task["max_steps"], int) and task["max_steps"] > 0


# ---------------------------------------------------------------------------
# 3. Mocked episode lifecycle
# ---------------------------------------------------------------------------

class TestEpisodeLifecycle:
    """Tests the reset → step → done lifecycle using a mocked httpx client."""

    def _make_env(self, mock_httpx_client):
        """Build an APIDebugEnvironment with httpx patched out."""
        # Patch httpx.Client used in api_debug_environment
        with patch("httpx.Client") as MockClient:
            cm = MockClient.return_value.__enter__.return_value
            cm.post.return_value = MagicMock(status_code=200, text="{}", headers={})
            cm.request.return_value = MagicMock(
                status_code=200,
                text='{"id": 1, "name": "alice"}',
                headers={"content-type": "application/json"},
            )
            import importlib
            import server.api_debug_environment as ade_module
            importlib.reload(ade_module)
            env = ade_module.APIDebugEnvironment()
        return env

    def test_reset_returns_observation(self):
        with patch("httpx.Client") as MockClient:
            cm = MockClient.return_value.__enter__.return_value
            cm.post.return_value = MagicMock(status_code=200, text="{}", headers={})
            from server.api_debug_environment import APIDebugEnvironment
            env = APIDebugEnvironment()
            obs = env.reset(task_id="easy")
            assert obs is not None
            assert hasattr(obs, "task_description")
            assert not obs.done

    def test_step_increments_step_count(self):
        with patch("httpx.Client") as MockClient:
            cm = MockClient.return_value.__enter__.return_value
            cm.post.return_value = MagicMock(status_code=200, text="{}", headers={})
            cm.request.return_value = MagicMock(
                status_code=200,
                text='{"id": 1, "name": "alice"}',
                headers={"content-type": "application/json"},
            )
            from server.api_debug_environment import APIDebugEnvironment
            from models import APIAction
            env = APIDebugEnvironment()
            env.reset(task_id="easy")
            action = APIAction(method="GET", url="/mock_api/users",
                               headers={}, body={}, query_params={})
            obs = env.step(action)
            assert env.state.step_count == 1
            assert obs.reward >= 0.001

    def test_done_when_max_steps_exceeded(self):
        with patch("httpx.Client") as MockClient:
            cm = MockClient.return_value.__enter__.return_value
            cm.post.return_value = MagicMock(status_code=200, text="{}", headers={})
            cm.request.return_value = MagicMock(
                status_code=404,
                text='{"detail":"not found"}',
                headers={},
            )
            from server.api_debug_environment import APIDebugEnvironment
            from models import APIAction
            env = APIDebugEnvironment()
            env.reset(task_id="easy")
            action = APIAction(method="GET", url="/mock_api/wrong",
                               headers={}, body={}, query_params={})
            max_steps = env.state.max_steps
            obs = None
            for _ in range(max_steps):
                obs = env.step(action)
            assert obs.done
