EXPERT_TASKS = [
    {
        "id": "expert_openapi_discovery",
        "description": "Log system metrics. We forgot the exact endpoint path and required schema. Check the server documentation at /openapi.json to discover the metrics ingestion endpoint under /mock_api, then send a valid POST payload with cpu_load and memory_usage.",
        "broken_request": {
            "method": "POST",
            "url": "/mock_api/unknown_metrics_endpoint",
            "headers": {"Content-Type": "application/json"},
            "body": {},
            "query_params": {},
        },
        "expected_status": 200,
        "expected_schema": {"status": "", "cpu": 0.0, "mem": 0.0},
        "max_steps": 10,
    },
    {
        "id": "expert_stateful_chain",
        "description": "First, create an item with name 'temporary_item' via POST /mock_api/items to get an auto-generated item_id. Then, safely clean it up by sending a DELETE request to /mock_api/items/{item_id}. The current request is a placeholder.",
        "broken_request": {
            "method": "POST",
            "url": "/mock_api/items",
            "headers": {"Content-Type": "application/json"},
            "body": {"name": "temporary_item"},
            "query_params": {},
        },
        "expected_status": 200,
        "expected_schema": {"status": "", "item_id": ""},
        "max_steps": 10,
    },
]