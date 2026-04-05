import json


class APIGrader:

    def grade(self, response_status, response_body, expected_status, expected_schema, attempt, max_steps):
        if response_status != expected_status:
            return self._partial(response_status)
        try:
            body = json.loads(response_body)
        except Exception:
            return 0.1
        schema_score = self._schema_match(body, expected_schema)
        attempt_bonus = max(0.0, 1.0 - (attempt / max_steps) * 0.15)
        return round(min(1.0, max(0.0, schema_score * attempt_bonus)), 4)

    def _partial(self, status):
        mapping = {0: 0.0, 401: 0.05, 403: 0.05, 404: 0.05, 405: 0.10, 415: 0.10, 422: 0.15, 429: 0.20, 200: 0.70}
        return mapping.get(status, 0.05)

    def _schema_match(self, body, schema):
        if not schema:
            return 1.0
        matched = sum(1 for k, v in schema.items() if k in body and type(body[k]) == type(v))
        return matched / len(schema)

    def get_feedback(self, status, expected_status):
        if status == expected_status:
            return "Correct status code. Verify response schema matches expected."
        hints = {
            401: "Authentication failed. Check Authorization header format and token value.",
            403: "Forbidden. Token valid but lacks permission.",
            404: "Endpoint not found. Check the URL path.",
            405: "Wrong HTTP method. Check if endpoint needs GET POST PUT or DELETE.",
            415: "Wrong Content-Type. Send application/json.",
            422: "Body validation failed. Check field names types and required fields.",
            429: "Rate limited. Add header X-Retry-After: 2 on next request.",
            500: "Server error. Your payload caused an exception.",
        }
        return hints.get(status, f"Got {status} expected {expected_status}. Re-read task description carefully.")
