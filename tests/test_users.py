import uuid
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_create_user():
    unique_id = uuid.uuid4()

    response = client.post("/users/", json={
        "username": f"Arthur-{unique_id}",
        "email": f"arthur-{unique_id}@test.com",
        "password": "testpass",
        "phone": "0600000000",
        "address": "Paris"
    })

    assert response.status_code == 201
    data = response.json()
    assert data["username"] == f"Arthur-{unique_id}"
    assert data["email"] == f"arthur-{unique_id}@test.com"
    assert data["phone"] == "0600000000"