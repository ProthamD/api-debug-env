import json


class APIGrader:

    def grade(self, response_status, response_body, expected_status, expected_schema, attempt, max_steps):
        if response_status != expected_status:
            return self._partial(response_status)
        try:
            body = json.loads(response_body)
        except Exception:
            return 0.25
        schema_score = self._schema_match(body, expected_schema)
        # Correct status always scores at least 0.25; attempt bonus tapers reward slightly
        base_score = max(0.25, schema_score)
        attempt_bonus = max(0.0, 1.0 - (attempt / max_steps) * 0.15)
        raw_score = base_score * attempt_bonus
        return round(min(0.999, max(0.001, raw_score)), 4)

    def _partial(self, status):
        # Partial credit for wrong-status responses — signals progress toward the solution
        mapping = {
            0:   0.001,   # connection error / no response
            401: 0.05,  # reached auth wall
            403: 0.05,  # reached permission wall
            404: 0.05,  # wrong endpoint
            405: 0.10,  # right endpoint, wrong method
            415: 0.10,  # right endpoint, wrong Content-Type
            422: 0.15,  # right endpoint+method, bad body schema
            429: 0.20,  # correct request but rate limited
        }
        return mapping.get(status, 0.05)

    def _schema_match(self, body, schema):
        if not schema:
            return 1.0
        matched = sum(1 for k, v in schema.items() if k in body and type(body[k]) == type(v))
        return matched / len(schema) if len(schema) > 0 else 1.0

    def get_feedback(self, status, expected_status):
        if status == expected_status:
            return "Correct status code. Verify response schema matches expected."
        hints = {
            401: "Authentication failed. The server could not verify your identity. Check your tokens or auth headers in the response.",
            403: "Forbidden. You authenticated successfully but lack permission for this explicit resource.",
            404: "Endpoint not found. Double-check the URL path and HTTP method.",
            405: "Method Not Allowed. The HTTP method used is not supported by this endpoint.",
            415: "Unsupported Media Type. The server expects a different Content-Type.",
            422: "Unprocessable Entity. The request body or query parameters failed validation. Check property names and data types.",
            429: "Too Many Requests. You have been rate limited. Look for a retry header.",
            500: "Internal Server Error. Your payload caused an unhandled exception.",
        }
        return hints.get(status, f"Received status {status}. Read the response body/headers for clues and retry.")
