def test_settings_get_and_update(client):
    client.post("/api/auth/setup", json={
        "email": "admin@test.com", "password": "password123", "confirm_password": "password123"
    })

    # Get settings (setup creates some default settings)
    response = client.get("/api/settings/")
    assert response.status_code == 200
    data = response.json()
    assert data.get("setup_completed") == True
    assert data.get("admin_email") == "admin@test.com"

    # Update bulk
    response = client.put("/api/settings/bulk", json={
        "default_target_lang": "JPN",
        "result_retention_days": 60
    })
    assert response.status_code == 200
    assert response.json()["message"] == "Settings updated"

    # Verify
    response = client.get("/api/settings/")
    data = response.json()
    assert data["default_target_lang"] == "JPN"
    assert data["result_retention_days"] == 60
