MEDIUM_TASKS = [
    {
        "id": "medium_wrong_method",
        "description": "Creating an order requires POST not GET. Fix the HTTP method and send body with product_id 5 and qty 2 to /mock_api/orders.",
        "broken_request": {
            "method": "GET",
            "url": "/mock_api/orders",
            "headers": {"Content-Type": "application/json"},
            "body": {"product_id": 5, "qty": 2},
            "query_params": {},
        },
        "expected_status": 200,
        "expected_schema": {"order_id": 0, "status": ""},
    },
    {
        "id": "medium_type_mismatch",
        "description": "The API expects product_id as an integer but the request sends the string five. Fix the type to the integer 5 in the body.",
        "broken_request": {
            "method": "POST",
            "url": "/mock_api/orders",
            "headers": {"Content-Type": "application/json"},
            "body": {"product_id": "five", "qty": 2},
            "query_params": {},
        },
        "expected_status": 200,
        "expected_schema": {"order_id": 0, "product_id": 0},
    },
    {
        "id": "medium_nested_field",
        "description": "The profile endpoint expects address to be a dict like street and city keys, not a plain string. Fix the body structure.",
        "broken_request": {
            "method": "POST",
            "url": "/mock_api/profile",
            "headers": {"Content-Type": "application/json"},
            "body": {"name": "Alice", "address": "123 Main St"},
            "query_params": {},
        },
        "expected_status": 200,
        "expected_schema": {"name": "", "address": {}, "updated": True},
    },
]
