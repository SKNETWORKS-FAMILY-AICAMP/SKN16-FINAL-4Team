from fastapi.testclient import TestClient
from services.api_image.main import app
import os

client = TestClient(app)


def test_ping():
    resp = client.get("/api/image/ping")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("service") == "api_image"


def test_predict_invalid_file():
    # Send an empty file -> should return 400
    files = {"file": ("empty.jpg", b"")}
    resp = client.post("/api/image/predict", files=files)
    assert resp.status_code == 400
