EASY_TASKS = [
    {
        "id": "easy_auth",
        "description": "The request is missing an Authorization header. The API requires: Authorization: Bearer demo_token_123. Fix the request to GET /mock_api/users successfully.",
        "broken_request": {
            "method": "GET",
            "url": "/mock_api/users",
            "headers": {},
            "body": None,
            "query_params": {},
        },
        "expected_status": 200,
        "expected_schema": {"users": []},
    },
    {
        "id": "easy_content_type",
        "description": "The request uses Content-Type: text/plain but the API requires application/json. Fix the header and send body with a name field to POST /mock_api/items.",
        "broken_request": {
            "method": "POST",
            "url": "/mock_api/items",
            "headers": {"Content-Type": "text/plain"},
            "body": None,
            "query_params": {},
        },
        "expected_status": 200,
        "expected_schema": {"item_id": 0, "name": "", "created": True},
    },
    {
        "id": "easy_query_param",
        "description": "The search endpoint requires a query parameter q. The request omits it. Add q=python to the query params for GET /mock_api/search.",
        "broken_request": {
            "method": "GET",
            "url": "/mock_api/search",
            "headers": {},
            "body": None,
            "query_params": {},
        },
        "expected_status": 200,
        "expected_schema": {"results": [], "total": 0},
    },
]
