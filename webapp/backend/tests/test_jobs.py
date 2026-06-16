import io
from PIL import Image


def _create_test_image():
    img = Image.new("RGB", (100, 100), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def test_job_lifecycle(client):
    client.post("/api/auth/setup", json={
        "email": "admin@test.com", "password": "password123", "confirm_password": "password123"
    })

    # Create collection + upload
    response = client.post("/api/collections/", json={"name": "Test"})
    coll_id = response.json()["id"]

    img = _create_test_image()
    response = client.post(
        "/api/uploads/",
        params={"collection_id": coll_id},
        files={"file": ("test.png", img, "image/png")}
    )
    assert response.status_code == 200
    asset_id = response.json()["asset_id"]

    # Create job
    response = client.post("/api/jobs/", json={
        "collection_id": coll_id,
        "name": "Test Job",
        "config_snapshot": {"translator": {"target_lang": "ENG"}}
    })
    assert response.status_code == 200
    job = response.json()
    assert job["status"] == "pending"
    job_id = job["id"]

    # List jobs
    response = client.get("/api/jobs/")
    assert response.status_code == 200
    assert len(response.json()) == 1

    # Get job with tasks
    response = client.get(f"/api/jobs/{job_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["job"]["id"] == job_id
    assert len(data["tasks"]) == 1

    # Cancel job
    response = client.post(f"/api/jobs/{job_id}/cancel")
    assert response.status_code == 200

    response = client.get(f"/api/jobs/{job_id}")
    assert response.json()["job"]["status"] == "cancelled"

    # Retry job
    response = client.post(f"/api/jobs/{job_id}/retry")
    assert response.status_code == 200

    response = client.get(f"/api/jobs/{job_id}")
    assert response.json()["job"]["status"] == "pending"
