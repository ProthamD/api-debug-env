import os
import json
import asyncio
from openai import OpenAI
from client import APIDebugEnv
from models import APIAction

API_BASE_URL = os.environ["API_BASE_URL"]
MODEL_NAME = os.environ["MODEL_NAME"]
HF_TOKEN = os.environ["HF_TOKEN"]
ENV_URL = os.environ.get("ENV_URL", "http://localhost:8000")

llm = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)

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


def call_llm(task_description, broken_request, last_status, last_body, feedback):
    user_msg = (
        f"Task: {task_description}\n\n"
        f"Broken request:\n{json.dumps(broken_request, indent=2)}\n\n"
        f"Last response status: {last_status}\n"
        f"Last response body: {last_body[:300]}\n\n"
        f"Feedback: {feedback}\n\n"
        f"Return the fixed request as JSON:"
    )
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
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return broken_request


async def run_task(env, task_id):
    obs = await env.reset(task_id=task_id)
    state = await env.state()

    print(json.dumps({
        "type": "[START]",
        "task_id": task_id,
        "episode_id": state.episode_id,
        "task_description": obs.task_description,
        "broken_request": obs.broken_request,
    }))

    final_reward = 0.0
    step_num = 0

    for step_num in range(state.max_steps):
        fixed = call_llm(
            obs.task_description,
            obs.broken_request,
            obs.last_status_code,
            obs.last_response_body,
            obs.step_feedback,
        )

        action = APIAction(
            method=str(fixed.get("method", "GET")),
            url=str(fixed.get("url", obs.broken_request.get("url", "/mock_api/users"))),
            headers=dict(fixed.get("headers") or {}),
            body=fixed.get("body"),
            query_params=dict(fixed.get("query_params") or {}),
        )

        result = await env.step(action)
        final_reward = result.reward
        obs = result.observation

        print(json.dumps({
            "type": "[STEP]",
            "task_id": task_id,
            "step": step_num + 1,
            "action": {
                "method": action.method,
                "url": action.url,
                "headers": action.headers,
                "body": action.body,
                "query_params": action.query_params,
            },
            "status_code": obs.last_status_code,
            "reward": result.reward,
            "done": result.done,
            "feedback": obs.step_feedback,
        }))

        if result.done:
            break

    print(json.dumps({
        "type": "[END]",
        "task_id": task_id,
        "final_reward": final_reward,
        "steps_taken": step_num + 1,
    }))

    return final_reward


async def main():
    async with APIDebugEnv(base_url=ENV_URL) as env:
        scores = {}
        for task_id in ["easy", "medium", "hard"]:
            scores[task_id] = await run_task(env, task_id)

        print(json.dumps({
            "type": "[SUMMARY]",
            "scores": scores,
            "average": round(sum(scores.values()) / len(scores), 4),
        }))


if __name__ == "__main__":
    asyncio.run(main())
