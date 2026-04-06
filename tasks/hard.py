HARD_TASKS = [
    {
        "id": "hard_token_exchange",
        "description": "Access the protected resource at GET /mock_api/protected. You might need to authenticate first to get a valid token. Valid credentials are client_id 'abc' and client_secret 'xyz' at /mock_api/auth/token.",
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
        "description": "Retrieve data from /mock_api/rate_limited. The server has strict rate limits. Continuously attempt to fetch until you get a successful 200 OK.",
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
        "description": "Fetch all logs from GET /mock_api/logs to get a 200 OK without more pages. The endpoint returns a cursor. Follow the cursor chain until has_more is false.",
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
