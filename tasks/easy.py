EASY_TASKS = [
    {
        "id": "easy_auth",
        "description": "Access the protected resource at GET /mock_api/users to get a 200 OK. The current request is failing.",
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
        "description": "Create an item with name 'test_item' via POST /mock_api/items to get a 200 OK. The current request payload is rejected by the server.",
        "broken_request": {
            "method": "POST",
            "url": "/mock_api/items",
            "headers": {"Content-Type": "text/plain"},
            "body": None,
            "query_params": {},
        },
        "expected_status": 200,
        "expected_schema": {"item_id": "", "name": "", "created": True},
    },
    {
        "id": "easy_query_param",
        "description": "Search for 'python' via GET /mock_api/search. The current request is missing required parameters.",
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
