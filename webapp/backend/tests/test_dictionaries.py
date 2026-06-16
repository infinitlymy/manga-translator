def test_dictionary_crud(client):
    # Setup auth
    client.post("/api/auth/setup", json={
        "email": "admin@test.com", "password": "password123", "confirm_password": "password123"
    })

    # Create a collection for context
    r = client.post("/api/collections/", json={"name": "Dict Test"})
    coll_id = r.json()["id"]

    # List dictionaries (should be empty)
    r = client.get("/api/dictionaries/", params={"collection_id": coll_id})
    assert r.status_code == 200
    assert r.json() == []

    # Create a post-translation term
    r = client.post("/api/dictionaries/", json={
        "collection_id": coll_id,
        "pattern": "hello",
        "replacement": "hola",
        "phase": "post",
        "note": "Spanish greeting",
    })
    assert r.status_code == 200
    term = r.json()
    assert term["pattern"] == "hello"
    assert term["replacement"] == "hola"
    assert term["phase"] == "post"
    assert term["usage_count"] == 0
    term_id = term["id"]

    # Create a pre-translation term
    r = client.post("/api/dictionaries/", json={
        "collection_id": coll_id,
        "pattern": "goodbye",
        "replacement": "adios",
        "phase": "pre",
    })
    assert r.status_code == 200
    pre_term = r.json()
    assert pre_term["phase"] == "pre"

    # List filtered by phase
    r = client.get("/api/dictionaries/", params={"collection_id": coll_id, "phase": "post"})
    assert r.status_code == 200
    assert len(r.json()) == 1

    # Update term
    r = client.put(f"/api/dictionaries/{term_id}", json={
        "replacement": "bonjour",
        "note": "French greeting",
    })
    assert r.status_code == 200
    assert r.json()["replacement"] == "bonjour"

    # Increment usage
    r = client.post(f"/api/dictionaries/{term_id}/increment-usage")
    assert r.status_code == 200
    assert r.json()["usage_count"] == 1
    assert r.json()["last_used_at"] is not None

    # Delete term
    r = client.delete(f"/api/dictionaries/{term_id}")
    assert r.status_code == 200

    # Verify deletion
    r = client.get("/api/dictionaries/", params={"collection_id": coll_id})
    assert len(r.json()) == 1
