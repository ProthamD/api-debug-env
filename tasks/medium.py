MEDIUM_TASKS = [
    {
        "id": "medium_wrong_method",
        "description": "Create an order for product_id 5 with qty 2 at /mock_api/orders. The given request is failing.",
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
        "description": "Submit a new order for product_id 5 and qty 2 at /mock_api/orders. The API is returning a validation error for the current payload.",
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
        "description": "Update the profile with name 'Alice' and address containing street '123 Main St' and city 'Metropolis'. The current payload structure is rejected.",
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
