HARD_TASKS = [
    {
        "id": "hard_token_exchange",
        "description": (
            "The protected endpoint needs a fresh token. "
            "Step 1: POST to /mock_api/auth/token with JSON body {\"client_id\": \"abc\", \"client_secret\": \"xyz\"} "
            "to get an access_token from the response. "
            "Step 2: Use that token as Authorization: Bearer <token> to GET /mock_api/protected. "
            "The token in the broken request is expired and will return 401."
        ),
        "broken_request": {
            "method": "GET",
            "url": "/mock_api/protected",
            "headers": {"Authorization": "Bearer stale_token_000"},
            "body": None,
            "query_params": {},
        },
        "expected_status": 200,
        "expected_schema": {"data": ""},
        "max_steps": 10,
    },
    {
        "id": "hard_rate_limit",
        "description": (
            "The rate_limited endpoint returns 429 after 3 requests without the X-Retry-After header. "
            "When you receive a 429, add the header X-Retry-After: 2 to your next request. "
            "The response body on 429 contains Retry-After hint in headers."
        ),
        "broken_request": {
            "method": "GET",
            "url": "/mock_api/rate_limited",
            "headers": {},
            "body": None,
            "query_params": {},
        },
        "expected_status": 200,
        "expected_schema": {"data": ""},
        "max_steps": 10,
    },
    {
        "id": "hard_pagination",
        "description": (
            "GET /mock_api/logs returns the first page with next_cursor and has_more fields. "
            "Pass cursor=<next_cursor> as a query param to get the next page. "
            "Keep following the cursor chain until has_more is false. "
            "The final page has has_more=false and no next_cursor."
        ),
        "broken_request": {
            "method": "GET",
            "url": "/mock_api/logs",
            "headers": {},
            "body": None,
            "query_params": {},
        },
        "expected_status": 200,
        "expected_schema": {"items": [], "has_more": False},
        "max_steps": 10,
    },
]
