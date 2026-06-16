def test_audit_log_and_revert(client):
    # Setup auth
    client.post("/api/auth/setup", json={
        "email": "admin@test.com", "password": "password123", "confirm_password": "password123"
    })

    # Create a collection (should generate audit log)
    r = client.post("/api/collections/", json={"name": "Audit Test", "series": "Demo"})
    coll_id = r.json()["id"]

    # Update it
    client.put(f"/api/collections/{coll_id}", json={"name": "Audit Test Updated"})

    # List audit logs
    r = client.get("/api/audit-log/")
    assert r.status_code == 200
    logs = r.json()
    assert len(logs) >= 2
    create_logs = [l for l in logs if l["action"] == "create" and l["table_name"] == "collections"]
    update_logs = [l for l in logs if l["action"] == "update" and l["table_name"] == "collections"]
    assert len(create_logs) == 1
    assert len(update_logs) == 1
    assert create_logs[0]["new_data"]["name"] == "Audit Test"
    assert update_logs[0]["old_data"]["name"] == "Audit Test"
    assert update_logs[0]["new_data"]["name"] == "Audit Test Updated"

    # Revert the update
    log_id = update_logs[0]["id"]
    r = client.post(f"/api/audit-log/{log_id}/revert")
    assert r.status_code == 200
    assert r.json()["message"] == "Change reverted"

    # Verify collection reverted
    r = client.get(f"/api/collections/{coll_id}")
    assert r.json()["name"] == "Audit Test"

    # Verify log marked reverted
    r = client.get(f"/api/audit-log/{log_id}")
    assert r.json()["reverted_at"] is not None

    # Double revert should fail
    r = client.post(f"/api/audit-log/{log_id}/revert")
    assert r.status_code == 400
