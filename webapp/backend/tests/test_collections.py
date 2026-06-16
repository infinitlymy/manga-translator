import io
from PIL import Image


def _create_test_image():
    img = Image.new("RGB", (100, 100), color="red")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def test_collection_crud(client):
    # Setup auth
    client.post("/api/auth/setup", json={
        "email": "admin@test.com", "password": "password123", "confirm_password": "password123"
    })

    # Create collection
    response = client.post("/api/collections/", json={"name": "My Manga", "description": "Test"})
    assert response.status_code == 200
    coll = response.json()
    assert coll["name"] == "My Manga"
    coll_id = coll["id"]

    # List collections
    response = client.get("/api/collections/")
    assert response.status_code == 200
    assert len(response.json()) == 1

    # Get collection
    response = client.get(f"/api/collections/{coll_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "My Manga"

    # Update collection
    response = client.put(f"/api/collections/{coll_id}", json={"name": "Updated Manga"})
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Manga"

    # Delete collection
    response = client.delete(f"/api/collections/{coll_id}")
    assert response.status_code == 200

    response = client.get("/api/collections/")
    assert len(response.json()) == 0


def test_collection_with_assets(client):
    client.post("/api/auth/setup", json={
        "email": "admin@test.com", "password": "password123", "confirm_password": "password123"
    })

    # Create collection
    response = client.post("/api/collections/", json={"name": "Test"})
    coll_id = response.json()["id"]

    # Upload image
    img = _create_test_image()
    response = client.post(
        "/api/uploads/",
        params={"collection_id": coll_id},
        files={"file": ("test.png", img, "image/png")}
    )
    assert response.status_code == 200
    asset_id = response.json()["asset_id"]

    # Get collection assets
    response = client.get(f"/api/collections/{coll_id}/assets")
    assert response.status_code == 200
    assert len(response.json()) == 1
