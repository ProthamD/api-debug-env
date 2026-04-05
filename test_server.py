from fastapi.testclient import TestClient
from server.app import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    print("health OK")

def test_reset():
    response = client.post("/reset", json={"task_id": "easy"})
    assert response.status_code == 200
    assert "task_description" in response.json()
    print("easy reset OK")

if __name__ == "__main__":
    test_health()
    test_reset()
    print("All tests passed.")
