import os
import json
import asyncio
import httpx
from typing import List, Optional
from openai import OpenAI

API_BASE_URL = os.getenv("API_BASE_URL") or "https://router.huggingface.co/v1"
MODEL_NAME = os.getenv("MODEL_NAME") or "mistralai/Mistral-7B-Instruct-v0.3"
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY") or "dummy"
ENV_URL = os.getenv("ENV_URL", "http://localhost:7860").rstrip("/")
BENCHMARK = "api_debug_env"
MAX_STEPS = 5
SUCCESS_SCORE_THRESHOLD = 0.8

llm = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

SYSTEM_PROMPT = """You are an HTTP API debugger. You receive a broken request and must fix it to get HTTP 200.
Respond ONLY in valid JSON with exactly these fields:
{
  "method": "GET",
  "url": "/mock_api/...",
  "headers": {},
  "body": null,
  "query_params": {}
}
Rules:
- method must be uppercase
- url must start with /mock_api/
- body must be null for GET requests
- always include Content-Type: application/json when body is not null
- do not add any text outside the JSON"""


def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}", flush=True)


def call_llm(task_description, broken_request, last_status, last_body, feedback):
    user_msg = (
        f"Task: {task_description}\n\n"
        f"Broken request:\n{json.dumps(broken_request, indent=2)}\n\n"
        f"Last response status: {last_status}\n"
        f"Last response body: {str(last_body)[:300]}\n\n"
        f"Feedback: {feedback}\n\n"
        f"Return the fixed request as JSON:"
    )
    try:
        resp = llm.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=300,
            temperature=0.1,
        )
        raw = resp.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(raw)
    except Exception:
        return broken_request


async def env_reset(client: httpx.AsyncClient, task_id: str) -> dict:
    resp = await client.post("/reset", json={"task_id": task_id}, timeout=30)
    resp.raise_for_status()
    return resp.json()


async def env_step(client: httpx.AsyncClient, action: dict) -> dict:
    resp = await client.post("/step", json={"action": action}, timeout=30)
    resp.raise_for_status()
    return resp.json()


async def env_state(client: httpx.AsyncClient) -> dict:
    resp = await client.get("/state", timeout=10)
    resp.raise_for_status()
    return resp.json()


async def run_task(client: httpx.AsyncClient, task_id: str) -> float:
    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False

    log_start(task=task_id, env=BENCHMARK, model=MODEL_NAME)

    try:
        obs = await env_reset(client, task_id)
        state = await env_state(client)
        max_steps = state.get("max_steps", MAX_STEPS)
        done = obs.get("done", False)

        for step in range(1, max_steps + 1):
            if done:
                break

            fixed = call_llm(
                obs.get("task_description", ""),
                obs.get("broken_request", {}),
                obs.get("last_status_code", 0),
                obs.get("last_response_body", ""),
                obs.get("step_feedback", ""),
            )

            action = {
                "method": str(fixed.get("method", "GET")),
                "url": str(fixed.get("url", "/mock_api/users")),
                "headers": dict(fixed.get("headers") or {}),
                "body": fixed.get("body") or None,
                "query_params": dict(fixed.get("query_params") or {}),
            }

            action_str = f"{action['method']}:{action['url']}"
            result = await env_step(client, action)

            reward = float(result.get("reward", 0.0))
            done = bool(result.get("done", False))
            obs = result.get("observation", result)

            rewards.append(reward)
            steps_taken = step

            log_step(step=step, action=action_str, reward=reward, done=done, error=None)

            if done:
                break

        score = max(rewards) if rewards else 0.0
        success = score >= SUCCESS_SCORE_THRESHOLD

    except Exception as e:
        print(f"[DEBUG] Task {task_id} error: {e}", flush=True)
        log_step(step=steps_taken, action="error", reward=0.0, done=True, error=str(e))

    finally:
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

    return score


async def main():
    async with httpx.AsyncClient(base_url=ENV_URL, timeout=30.0) as client:
        # Verify environment is reachable
        try:
            health = await client.get("/health")
            health.raise_for_status()
        except Exception as e:
            print(f"[DEBUG] Environment not reachable at {ENV_URL}: {e}", flush=True)
            raise

        for task_id in ["easy", "medium", "hard"]:
            await run_task(client, task_id)


if __name__ == "__main__":
    asyncio.run(main())