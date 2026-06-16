def test_setup_status_empty_db(client):
    response = client.get("/api/setup-status")
    assert response.status_code == 200
    assert response.json() == {"setup_completed": False}


def test_setup_and_login(client):
    # Setup
    response = client.post("/api/auth/setup", json={
        "email": "admin@test.com",
        "password": "password123",
        "confirm_password": "password123",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "admin@test.com"
    assert data["role"] == "admin"

    # Setup should now be completed
    response = client.get("/api/setup-status")
    assert response.json() == {"setup_completed": True}

    # Login
    response = client.post("/api/auth/login", json={
        "email": "admin@test.com",
        "password": "password123",
    })
    assert response.status_code == 200
    login_data = response.json()
    assert "access_token" in login_data
    assert "refresh_token" in login_data

    # Get me
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    me = response.json()
    assert me["email"] == "admin@test.com"

    # Logout
    response = client.post("/api/auth/logout")
    assert response.status_code == 200


def test_setup_duplicate_fails(client):
    client.post("/api/auth/setup", json={
        "email": "admin@test.com",
        "password": "password123",
        "confirm_password": "password123",
    })
    response = client.post("/api/auth/setup", json={
        "email": "admin2@test.com",
        "password": "password123",
        "confirm_password": "password123",
    })
    assert response.status_code == 409


def test_login_invalid_credentials(client):
    client.post("/api/auth/setup", json={
        "email": "admin@test.com",
        "password": "password123",
        "confirm_password": "password123",
    })
    response = client.post("/api/auth/login", json={
        "email": "admin@test.com",
        "password": "wrongpassword",
    })
    assert response.status_code == 401
