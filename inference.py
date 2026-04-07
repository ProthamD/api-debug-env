"""
Inference Script for API Debug Environment
===========================================
Mandatory stdout format per Phase 2 validator:
  [START] task=<task_name> env=<benchmark> model=<model_name>
  [STEP]  step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
  [END]   success=<true|false> steps=<n> score=<score> rewards=<r1,r2,...,rn>
"""

import os
import json
import asyncio
import httpx
from typing import List, Optional
from openai import OpenAI

# ── Environment variables ──────────────────────────────────────────────────────
API_BASE_URL = os.getenv("API_BASE_URL") or "https://router.huggingface.co/v1"
MODEL_NAME   = os.getenv("MODEL_NAME")   or "mistralai/Mistral-7B-Instruct-v0.3"
API_KEY      = os.getenv("HF_TOKEN")     or os.getenv("API_KEY") or "dummy"
ENV_URL      = os.getenv("ENV_URL", "http://localhost:7860").rstrip("/")

BENCHMARK = "api_debug_env"

# Max steps per difficulty (mirrors openenv.yaml config so we don't rely on /state)
TASK_MAX_STEPS = {
    "easy":   5,
    "medium": 5,
    "hard":   10,
    "expert": 10,
}
DEFAULT_MAX_STEPS    = 5
SUCCESS_SCORE_THRESHOLD = 0.8

# ── LLM client ─────────────────────────────────────────────────────────────────
llm = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

SYSTEM_PROMPT = """\
You are an HTTP API debugger. You receive a broken HTTP request and must fix it to get HTTP 200.
Respond ONLY in valid JSON with exactly these fields:
{
  "method": "GET",
  "url": "/mock_api/...",
  "headers": {},
  "body": null,
  "query_params": {}
}
Rules:
- method must be uppercase (GET, POST, DELETE, etc.)
- url must start with /mock_api/
- body must be null for GET/DELETE requests
- always include Content-Type: application/json when body is not null
- do not add any text outside the JSON
- read the task description carefully and produce the correct fix on the first attempt"""


# ── Logging helpers ────────────────────────────────────────────────────────────
def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool,
             error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val  = str(done).lower()
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f}"
        f" done={done_val} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float,
            rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps}"
        f" score={score:.3f} rewards={rewards_str}",
        flush=True,
    )


# ── LLM call ──────────────────────────────────────────────────────────────────
def call_llm(task_description: str, broken_request: dict,
             last_status: int, last_body: str, feedback: str,
             history: List[str]) -> dict:
    """Ask the LLM to fix the broken request. Returns a request dict."""
    history_str = "\n".join(history[-3:]) if history else "None"
    user_msg = (
        f"Task description:\n{task_description}\n\n"
        f"Broken request (JSON):\n{json.dumps(broken_request, indent=2)}\n\n"
        f"Last response status: {last_status}\n"
        f"Last response body: {str(last_body)[:400]}\n\n"
        f"Server feedback: {feedback}\n\n"
        f"Previous attempts (latest first):\n{history_str}\n\n"
        f"Return the corrected request as JSON:"
    )
    try:
        resp = llm.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_msg},
            ],
            max_tokens=350,
            temperature=0.0,   # deterministic for API debugging
        )
        raw = (resp.choices[0].message.content or "").strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        return json.loads(raw)
    except json.JSONDecodeError:
        # LLM returned non-JSON — try to extract the first {...} block
        try:
            start = raw.index("{")
            end   = raw.rindex("}") + 1
            return json.loads(raw[start:end])
        except Exception:
            pass
    except Exception:
        pass
    # Last-resort fallback: return broken_request unchanged so the loop
    # can still emit a [STEP] line with error context
    return broken_request


# ── Environment HTTP helpers ───────────────────────────────────────────────────
async def env_reset(client: httpx.AsyncClient, task_id: str) -> dict:
    """POST /reset and return the parsed JSON body."""
    try:
        resp = await client.post(
            "/reset",
            json={"task_id": task_id},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(f"env_reset HTTP error {exc.response.status_code}: "
                           f"{exc.response.text[:200]}") from exc
    except Exception as exc:
        raise RuntimeError(f"env_reset failed: {exc}") from exc


async def env_step(client: httpx.AsyncClient, action: dict) -> dict:
    """POST /step and return the parsed JSON body."""
    try:
        resp = await client.post(
            "/step",
            json={"action": action},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(f"env_step HTTP error {exc.response.status_code}: "
                           f"{exc.response.text[:200]}") from exc
    except Exception as exc:
        raise RuntimeError(f"env_step failed: {exc}") from exc


# ── Per-task episode runner ────────────────────────────────────────────────────
async def run_task(client: httpx.AsyncClient, task_id: str) -> float:
    rewards:     List[float] = []
    steps_taken: int         = 0
    score:       float       = 0.001   # default: strictly > 0 for Phase 2
    success:     bool        = False
    history:     List[str]   = []

    # Per-task max steps (matches openenv.yaml; /state doesn't expose these)
    max_steps = TASK_MAX_STEPS.get(task_id, DEFAULT_MAX_STEPS)

    log_start(task=task_id, env=BENCHMARK, model=MODEL_NAME)

    try:
        # ── Reset ────────────────────────────────────────────────────────────
        reset_resp = await env_reset(client, task_id)
        obs        = reset_resp.get("observation", reset_resp)
        done       = bool(reset_resp.get("done", False))

        # ── Step loop ─────────────────────────────────────────────────────────
        for step in range(1, max_steps + 1):
            if done:
                break

            # Build LLM prompt context
            task_desc   = obs.get("task_description",  "")
            broken_req  = obs.get("broken_request",    {})
            last_status = obs.get("last_status_code",  0)
            last_body   = obs.get("last_response_body", "")
            feedback    = obs.get("step_feedback",     "")

            # Ask LLM to fix the request
            fixed = call_llm(
                task_desc, broken_req, last_status, last_body,
                feedback, history,
            )

            # Sanitise the LLM output into a clean action dict
            method = str(fixed.get("method", "GET")).upper()
            url    = str(fixed.get("url", "/mock_api/users"))

            # Body must be None for GET/DELETE; otherwise keep what LLM says
            body = fixed.get("body")
            if method in ("GET", "DELETE", "HEAD"):
                body = None

            action = {
                "method":       method,
                "url":          url,
                "headers":      dict(fixed.get("headers") or {}),
                "body":         body if body is not None else {},
                "query_params": dict(fixed.get("query_params") or {}),
            }

            action_str = f"{method}:{url}"

            # ── Step ──────────────────────────────────────────────────────────
            try:
                result = await env_step(client, action)
                reward = float(result.get("reward", 0.0))
                done   = bool(result.get("done", False))
                obs    = result.get("observation", result)
                error_str: Optional[str] = None
            except RuntimeError as exc:
                reward    = 0.0
                done      = True          # abort episode on env error
                error_str = str(exc)[:120]

            rewards.append(reward)
            steps_taken = step

            log_step(step=step, action=action_str, reward=reward,
                     done=done, error=error_str)

            history.append(
                f"step={step} action={action_str} "
                f"status={obs.get('last_status_code', '?')} "
                f"reward={reward:.2f}"
            )

            if done:
                break

        # Score: best single-step reward achieved during the episode.
        # Phase 2 requires score strictly in (0, 1) — clamp away from boundaries.
        _raw    = max(rewards) if rewards else 0.0
        score   = max(0.001, min(0.999, _raw))
        success = score >= SUCCESS_SCORE_THRESHOLD

    except Exception as exc:
        # Unexpected outer exception — still must emit [END]
        print(f"[DEBUG] run_task({task_id}) outer exception: {exc}", flush=True)
        if steps_taken == 0:
            # We haven't emitted a single [STEP]; emit a dummy one so the
            # Phase 2 validator can parse a proper log
            log_step(step=1, action="error", reward=0.001, done=True,
                     error=str(exc)[:120])
            steps_taken = 1
            rewards = [0.001]

    finally:
        log_end(success=success, steps=steps_taken,
                score=score, rewards=rewards)

    return score


# ── Entry point ───────────────────────────────────────────────────────────────
async def main() -> None:
    async with httpx.AsyncClient(base_url=ENV_URL, timeout=30.0) as client:
        # Verify env is reachable — log warning but ALWAYS proceed so that
        # mandatory [START]/[END] lines are emitted for every task.
        try:
            health = await client.get("/health", timeout=10)
            health.raise_for_status()
            print(f"[DEBUG] Environment reachable at {ENV_URL}", flush=True)
        except Exception as exc:
            print(
                f"[DEBUG] Environment not reachable at {ENV_URL}: {exc}",
                flush=True,
            )
            # Do NOT return — we must still run tasks to emit required log lines

        for task_id in ["easy", "medium", "hard", "expert", "auto"]:
            await run_task(client, task_id)


if __name__ == "__main__":
    asyncio.run(main())