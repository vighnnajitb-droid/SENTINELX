import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_integration_workflow():
    # Force the startup event to run to create the user
    from seed_db import seed_admin
    seed_admin("admin", "admin")
    
    # 1. Login
    resp = client.post("/api/v1/auth/login", data={"username": "admin", "password": "admin"})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Upload Log
    with open("sample_data/suspicious_activity.csv", "rb") as f:
        resp = client.post(
            "/api/v1/logs/upload", 
            headers=headers, 
            files={"file": ("suspicious_activity.csv", f, "text/csv")}
        )
        assert resp.status_code == 200, f"Upload failed: {resp.text}"
        incident_id = resp.json()["incident_id"]
        
    # 3. Start Investigation (sync for test client but it spawns a background task)
    # Background tasks in TestClient run synchronously after the response is returned!
    resp = client.post(f"/api/v1/investigations/{incident_id}/run", headers=headers)
    assert resp.status_code == 200, f"Investigation start failed: {resp.text}"
    investigation_id = resp.json()["investigation_id"]
    
    # 4. Wait/Check for investigation to complete
    resp = client.get(f"/api/v1/investigations/{investigation_id}", headers=headers)
    assert resp.status_code == 200
    status = resp.json()["status"]
    
    assert status in ["completed", "awaiting_review"]
    
    # 5. Approve recommendation
    if status == "awaiting_review":
        resp = client.post(f"/api/v1/approvals/{investigation_id}", headers=headers, json={"action": "approve"})
        assert resp.status_code == 200, f"Approval failed: {resp.text}"
    
    # 6. Check Audit Logs
    resp = client.get(f"/api/v1/incidents/{incident_id}/audit", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) > 0
    print("Integration test passed successfully!")

