HARD_TASKS = [
    {
        "id": "hard_token_exchange",
        "description": "The protected endpoint needs a fresh token. First POST to /mock_api/auth/token with body client_id abc and client_secret xyz to get an access_token. Then use it as Authorization: Bearer <token> to GET /mock_api/protected. The token in the broken request is expired.",
        "broken_request": {
            "method": "GET",
            "url": "/mock_api/protected",
            "headers": {"Authorization": "Bearer stale_token_000"},
            "body": None,
            "query_params": {},
        },
        "expected_status": 200,
        "expected_schema": {"data": ""},
    },
    {
        "id": "hard_rate_limit",
        "description": "The rate_limited endpoint returns 429 if you send more than 3 requests without the X-Retry-After header. After receiving a 429 include header X-Retry-After with value 2.",
        "broken_request": {
            "method": "GET",
            "url": "/mock_api/rate_limited",
            "headers": {},
            "body": None,
            "query_params": {},
        },
        "expected_status": 200,
        "expected_schema": {"data": ""},
    },
    {
        "id": "hard_pagination",
        "description": "GET /mock_api/logs returns only the first page with a next_cursor field. Follow the cursor chain by passing cursor as a query param until has_more is false.",
        "broken_request": {
            "method": "GET",
            "url": "/mock_api/logs",
            "headers": {},
            "body": None,
            "query_params": {},
        },
        "expected_status": 200,
        "expected_schema": {"items": [], "has_more": False},
    },
]
