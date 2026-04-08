---
title: API Debug Env
emoji: 🔧
colorFrom: blue
colorTo: green
sdk: docker
pinned: false
---

# API Debug Environment

> A real-world OpenEnv environment where AI agents learn to debug broken HTTP API requests.

Built for the **Scaler × Meta PyTorch × HuggingFace OpenEnv Hackathon 2026**.

---

## What This Environment Does

An AI agent is given a **broken HTTP request** and a task description. It interacts with a live mock REST API running inside the same container, reads the real HTTP error responses (401, 422, 429, 500), and iteratively fixes its requests — adjusting headers, methods, body types, and authentication flows — until it receives a successful 200 response.

Every step produces a real HTTP call. The grader is fully deterministic: no LLM, no fuzzy matching. The reward is derived entirely from HTTP status codes and response schema matching.

---

## Environment Summary

| Property | Value |
|---|---|
| **Framework** | OpenEnv (openenv-core 0.2.3) |
| **Tasks** | 4 difficulty levels — 12 tasks total |
| **Max Steps per Episode** | Dynamic (10 by default) |
| **Reward Range** | 0.001 – 0.999 (Strictly bounded) |
| **Curriculum** | Supports automatic difficulty progression (`task_id: "auto"`) with exploration bonuses |
| **Grader** | Fully deterministic (no LLM), robust to negative reward hacking. Supports multi-step stateful evaluation. |
| **Mock API** | Internal FastAPI router, same container |
| **State Reset** | Secure `/_admin/reset` injects completely dynamic schemas, tokens, and routes per episode! |
| **Port** | 7860 (HF Spaces) |

---

## Action Space

The agent sends a structured HTTP request at each step.

| Field | Type | Description |
|---|---|---|
| `method` | `str` | HTTP method — `GET`, `POST`, `PUT`, `DELETE`, `PATCH` |
| `url` | `str` | Endpoint path e.g. `/mock_api/users` |
| `headers` | `dict` | Request headers e.g. `{"Authorization": "Bearer token"}` |
| `body` | `dict` | Request body — `null` for GET requests |
| `query_params` | `dict` | URL query parameters e.g. `{"q": "python"}` |

---

## Observation Space

After each step the agent receives:

| Field | Type | Description |
|---|---|---|
| `task_id` | `str` | Current task — `easy`, `medium`, or `hard` |
| `task_description` | `str` | Plain-English description of what needs to be fixed |
| `broken_request` | `dict` | The original broken request shown at episode start |
| `last_status_code` | `int` | HTTP status from last step (0 = not yet tried) |
| `last_response_headers` | `dict` | Response headers from last step |
| `last_response_body` | `str` | Raw response body from last step |
| `step_feedback` | `str` | Human-readable hint based on last error |
| `current_score` | `float` | Running reward 0.0–1.0 |
| `reward` | `float` | Reward for the last step |
| `done` | `bool` | Whether the episode has ended |
| `attempt` | `int` | Current step number |

---

## Tasks

### Easy — Auth and Header Errors

Simple fixes to authentication headers and request format.

| Task ID | Bug | What the Agent Needs to Fix |
|---|---|---|
| `easy_auth` | Missing `Authorization` header | Add `Authorization: Bearer demo_token_123` to GET `/mock_api/users` |
| `easy_content_type` | Wrong `Content-Type: text/plain` | Change to `application/json` and add `{"name": "book"}` body to POST `/mock_api/items` |
| `easy_query_param` | Missing `?q=` query param | Add `q=python` to GET `/mock_api/search` |

### Medium — Method and Body Errors

Requires understanding API semantics and request structure.

| Task ID | Bug | What the Agent Needs to Fix |
|---|---|---|
| `medium_wrong_method` | `GET` instead of `POST` | Change method to POST on `/mock_api/orders` |
| `medium_type_mismatch` | `product_id: "five"` (string) | Fix to integer `5` in body |
| `medium_nested_field` | `address: "123 Main St"` (string) | Fix to dict `{"street": "123 Main St", "city": "NY"}` |

### Hard — Rate Limiting and Multi-step Auth

Requires multi-step reasoning and handling stateful API behaviour.

| Task ID | Bug | What the Agent Needs to Fix |
|---|---|---|
| `hard_token_exchange` | Stale/expired Bearer token | First POST to `/mock_api/auth/token` to get a fresh token, then use it on GET `/mock_api/protected` |
| `hard_rate_limit` | No backoff after 429 | After receiving 429, include `X-Retry-After: 2` header on next request |
| `hard_pagination` | Never follows cursor | Call GET `/mock_api/logs?cursor=<value>` until `has_more` is `false` |

### Expert — Sandbox & Undocumented APIs

Advanced RL environment forcing pure systematic exploration and state tracking.

| Task ID | Bug | What the Agent Needs to Fix |
|---|---|---|
| `expert_openapi_discovery` | Completely undocumented endpoint | Query `/mock_api/system/metrics` utilizing OPTIONS/Swagger to find correct schema |
| `expert_stateful_chain` | UUIDs change every run | Create a user, extract the generated `user_id`, and immediately update their preferences |
| `expert_transaction_rollback` | Multi-step transaction | Begin a transaction, fail it intentionally, and issue a rollback command cleanly |

---

## Reward Function

```
base_score = schema_match_score
attempt_bonus = max(0.0, 1.0 − (attempt / max_steps) × 0.15)
exploration_bonus = 0.05 per successfully reached novel endpoint

reward = round(min(0.999, max(0.001, base_score × attempt_bonus + exploration_bonus)), 4)
```

Agents are rewarded more for solving tasks in fewer steps. Partial credit is given at every step:

| HTTP Status Received | Partial Reward | Meaning |
|---|---|---|
| 0 | 0.001 | Request never sent / connection error |
| 401 / 403 / 404 | ~0.05 | Hit the endpoint, auth failed |
| 405 / 415 | ~0.10 | Auth ok, wrong method or content-type |
| 422 | ~0.15 | Auth ok, body validation failed |
| 429 | ~0.20 | Hit endpoint, needs rate limit handling |
| 200 (schema mismatch) | ~0.25 | Right status, wrong response structure |
| 200 (schema match) | 0.85–0.999 | Correct — higher reward for fewer attempts |

---

## 🚀 Advanced Environment Capabilities

* **Dynamic Data Generation**: To destroy brute-force LLM memorization, the `/_admin/reset` logic generates random `uuid`-based API tokens and randomly shifts required JSON key structures (e.g. `body["name"]` vs `body["dynamic_item_field"]`) at the start of every episode.
* **Exploration Bonus & Curriculum**: Agents receive a steady $+0.05$ reward for investigating new HTTP routes successfully. By specifying `task_id="auto"`, the RL environment tracks cross-episode metrics, automatically promoting the model's difficulty curriculum without external scaffolding!
* **Multi-Step Array Grading**: The deterministic grader processes tasks over multi-step state arrays. Tasks like `expert_stateful_chain` require sequenced POST & DELETE combos cleanly scored progressively.

---

## Mock API Endpoints

All endpoints are mounted at `/mock_api/` inside the same container — no external calls, fully reproducible.

| Method | Path | What it Does | Common Error |
|---|---|---|---|
| `GET` | `/mock_api/users` | Returns user list | 401 if no Bearer token |
| `POST` | `/mock_api/items` | Creates an item | 415 if wrong Content-Type, 422 if no `name` |
| `GET` | `/mock_api/search` | Search results | 422 if no `?q=` param |
| `POST` | `/mock_api/orders` | Creates an order | 405 if GET, 422 if wrong types |
| `POST` | `/mock_api/profile` | Updates profile | 422 if `address` is not a dict |
| `POST` | `/mock_api/auth/token` | Issues a token | 401 if wrong credentials |
| `GET` | `/mock_api/protected` | Protected resource | 401 if token not from `/auth/token` |
| `GET` | `/mock_api/rate_limited` | Rate-limited resource | 429 after 3 requests without `X-Retry-After` |
| `GET` | `/mock_api/logs` | Paginated log entries | Returns cursor — must follow chain |

---

## API Endpoints (OpenEnv)

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check — returns `{"status": "ok"}` |
| `POST` | `/reset` | Start new episode. Body: `{"task_id": "easy"}` |
| `POST` | `/step` | Execute action. Body: `{"action": {...}}` |
| `GET` | `/state` | Get current episode state |
| `GET` | `/docs` | Auto-generated Swagger UI |

---

## Quick Start

### Connect to the deployed Space

```python
from client import APIDebugEnv
from models import APIAction

with APIDebugEnv(base_url="https://ProthamD-api-debug-env.hf.space").sync() as env:
    # Start an episode
    obs = env.reset(task_id="easy")
    print(obs.task_description)
    print(obs.broken_request)

    # Fix the request and step
    result = env.step(APIAction(
        method="GET",
        url="/mock_api/users",
        headers={"Authorization": "Bearer demo_token_123"},
        body=None,
        query_params={}
    ))
    print(result.reward)       # 0.85+
    print(result.observation.step_feedback)
```

### Install the client

```bash
pip install git+https://huggingface.co/spaces/ProthamD/api-debug-env
```

### Run locally with Docker

```bash
docker pull registry.hf.space/ProthamD-api-debug-env:latest
docker run -p 7860:7860 registry.hf.space/ProthamD-api-debug-env:latest
```

---

## Run the Baseline Inference Script

```bash
# Set environment variables
export API_BASE_URL=https://router.huggingface.co/v1
export MODEL_NAME=mistralai/Mistral-7B-Instruct-v0.3
export HF_TOKEN=hf_your_token_here
export ENV_URL=https://ProthamD-api-debug-env.hf.space

# Run
python inference.py
```

### Expected log format

```json
[START] task=easy env=api_debug_env model=mistralai/Mistral-7B-Instruct-v0.3
[STEP] step=1 action={"method":"GET","url":"/mock_api/users",...} reward=0.05 done=false error=null
[STEP] step=2 action={"method":"GET","url":"/mock_api/users","headers":{"Authorization":"Bearer demo_token_123"},...} reward=0.92 done=true error=null
[END] success=true steps=2 score=0.920 rewards=0.05,0.92
```

---

## Project Structure

```
api_debug_env/
├── inference.py              ← Baseline inference script (root, mandatory)
├── models.py                 ← APIAction, APIObservation, APIState
├── client.py                 ← APIDebugEnv(EnvClient)
├── openenv.yaml              ← Environment manifest
├── pyproject.toml            ← Package config
├── Dockerfile                ← HF Spaces Dockerfile (port 7860)
├── tasks/
│   ├── easy.py               ← 3 easy tasks
│   ├── medium.py             ← 3 medium tasks
│   ├── hard.py               ← 3 hard/multi-step tasks
│   ├── expert.py             ← 3 expert advanced RL tasks
│   └── registry.py           ← TASK_REGISTRY dict
├── graders/
│   └── grader.py             ← Deterministic reward logic
├── tests/                    ← New! Unit tests for environment & grader
│   ├── __init__.py
│   └── test_environment.py
├── server/
    ├── app.py                ← FastAPI app with create_app()
    ├── api_debug_environment.py  ← Environment logic
    ├── mock_api.py           ← Internal mock REST API router
    └── requirements.txt
```

---

## Setup from Source

```bash
git clone https://huggingface.co/spaces/ProthamD/api-debug-env
cd api-debug-env

pip install openenv-core fastapi uvicorn httpx pydantic openai python-dotenv

# Windows
$env:PYTHONPATH = "path\to\api-debug-env"

# Linux/Mac
export PYTHONPATH=$(pwd)

uvicorn server.app:app --host 0.0.0.0 --port 7860
```

Test it:
```bash
curl http://localhost:7860/health
curl -X POST http://localhost:7860/reset \
  -H "Content-Type: application/json" \
  -d '{"task_id": "easy"}'
```

---

## 🧪 Testing

The environment includes a comprehensive test suite covering the grader, task registry, and episode lifecycle.

```bash
# Run all tests
python -m pytest tests/ -v
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `API_BASE_URL` | Yes | LLM API endpoint e.g. `https://router.huggingface.co/v1` |
| `MODEL_NAME` | Yes | Model identifier e.g. `mistralai/Mistral-7B-Instruct-v0.3` |
| `HF_TOKEN` | Yes | HuggingFace token with inference access |
| `ENV_URL` | No | Override environment URL (default: localhost) |
| `MOCK_BASE_URL` | No | Internal URL for the Mock API (default: http://localhost:7860) |

---

## Why API Debugging?

Debugging broken HTTP requests is one of the most common real-world developer tasks. Every backend developer, DevOps engineer, and API integrator does this daily. Unlike existing OpenEnv environments (games, code execution, financial simulations), there was no environment for this domain.

Key advantages of this domain for RL training:
- **Deterministic grading** — HTTP status codes are binary, no LLM judge needed
- **Rich partial reward signal** — agent gets meaningful feedback at every step
- **Stateful multi-turn reasoning** — hard tasks require chaining multiple requests
- **Real-world transferability** — skills learned here apply directly to production debugging

---

## License

MIT

## Author

Pratham Dey (ProthamD) — IIEST Shibpur, Information Technology