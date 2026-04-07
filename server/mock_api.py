import time
import uuid
from fastapi import APIRouter, Header, HTTPException, Request, Query
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/mock_api", tags=["mock"])

_issued_tokens = set()
_request_log = {}
_items_db = {}

DYNAMIC_CONFIG = {
    "demo_token": "demo_token_123",
    "client_id": "abc",
    "client_secret": "xyz",
    "dynamic_item_field": "name"
}

LOG_PAGES = {
    None: {"items": list(range(10)), "next_cursor": "cur_abc", "has_more": True},
    "cur_abc": {"items": list(range(10, 20)), "next_cursor": "cur_def", "has_more": True},
    "cur_def": {"items": list(range(20, 25)), "next_cursor": None, "has_more": False},
}

@router.post("/_admin/reset")
async def admin_reset(config: Optional[dict] = None):
    _issued_tokens.clear()
    _request_log.clear()
    _items_db.clear()
    if config:
        DYNAMIC_CONFIG.update(config)
    return {"status": "reset_successful"}


class TokenRequest(BaseModel):
    client_id: str
    client_secret: str

@router.post("/auth/token")
async def get_token(body: TokenRequest):
    if body.client_id == DYNAMIC_CONFIG["client_id"] and body.client_secret == DYNAMIC_CONFIG["client_secret"]:
        token = f"tok_{int(time.time())}"
        _issued_tokens.add(token)
        return {"access_token": token, "expires_in": 60}
    raise HTTPException(status_code=401, detail="Invalid client credentials")


@router.get("/users")
async def get_users(authorization: Optional[str] = Header(default=None)):
    dt = DYNAMIC_CONFIG["demo_token"]
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail=f"Authorization header missing or malformed. Expected format: Bearer <token>. Use '{dt}' for testing.")
    token = authorization.split(" ")[1]
    if token not in _issued_tokens and token != dt:
        raise HTTPException(status_code=401, detail=f"Invalid token. Try '{dt}'.")
    return {"users": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]}


@router.post("/items")
async def create_item(request: Request):
    ct = request.headers.get("content-type", "")
    if "application/json" not in ct:
        raise HTTPException(status_code=415, detail="Content-Type must be application/json")
    body = await request.json()
    field = DYNAMIC_CONFIG.get("dynamic_item_field", "name")
    if field not in body:
        raise HTTPException(status_code=422, detail=[{"loc": ["body", field], "msg": "field required"}])
    item_id = str(uuid.uuid4())
    _items_db[item_id] = body[field]
    return {"item_id": item_id, "name": body[field], "created": True}

@router.delete("/items/{item_id}")
async def delete_item(item_id: str):
    if item_id not in _items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    del _items_db[item_id]
    return {"status": "deleted", "item_id": item_id}


@router.get("/search")
async def search(q: Optional[str] = Query(default=None)):
    if not q:
        raise HTTPException(status_code=422, detail=[{"loc": ["query", "q"], "msg": "field required"}])
    return {"results": [{"title": f"Result for {q}", "score": 0.95}], "total": 1}


class OrderBody(BaseModel):
    product_id: int
    qty: int


@router.post("/orders")
async def create_order(order: OrderBody):
    return {"order_id": 999, "product_id": order.product_id, "qty": order.qty, "status": "confirmed"}


class AddressModel(BaseModel):
    street: str
    city: str


class ProfileBody(BaseModel):
    name: str
    address: AddressModel


@router.post("/profile")
async def update_profile(profile: ProfileBody):
    return {"name": profile.name, "address": profile.address.model_dump(), "updated": True}


@router.get("/protected")
async def protected(authorization: Optional[str] = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header missing")
    token = authorization.split(" ")[1]
    if token not in _issued_tokens:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return {"data": "secret_payload", "accessed_at": int(time.time())}


@router.get("/rate_limited")
async def rate_limited(request: Request, x_retry_after: Optional[str] = Header(default=None)):
    client_id = request.client.host if request.client else "default"
    now = time.time()
    window = [t for t in _request_log.get(client_id, []) if now - t < 5]
    if len(window) >= 3 and not x_retry_after:
        _request_log[client_id] = window
        raise HTTPException(
            status_code=429, 
            detail={"error": "Rate limit exceeded", "hint": "Please add X-Retry-After header with value 2 to override."},
            headers={"Retry-After": "2"}
        )
    window.append(now)
    _request_log[client_id] = window
    return {"data": "rate_limited_resource", "requests_in_window": len(window)}


@router.get("/logs")
async def get_logs(cursor: Optional[str] = Query(default=None)):
    if cursor not in LOG_PAGES:
        raise HTTPException(status_code=400, detail=f"Invalid cursor: {cursor}")
    return LOG_PAGES[cursor]

class MetricsBody(BaseModel):
    cpu_load: float
    memory_usage: float

@router.post("/system/metrics", description="Ingest system metrics. Required JSON fields: cpu_load (float), memory_usage (float).")
async def ingest_metrics(metrics: MetricsBody):
    return {"status": "metrics_logged", "cpu": metrics.cpu_load, "mem": metrics.memory_usage}
