import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.api.accounts import AUTH_SESSIONS

client = TestClient(app)

@pytest.fixture(autouse=True)
def authenticate_client():
    client.post("/api/v1/auth/login", json={
        "email": "vivek.admin@msedcl.gov.in",
        "password": "EnterpriseSecPass2026!"
    })

def test_list_providers_and_capabilities():
    response = client.get("/api/v1/providers")
    assert response.status_code == 200
    providers = response.json()
    assert len(providers) >= 4
    
    # Check that Google Drive, OneDrive, and Dropbox have documented capability flags
    p_map = {p["id"]: p["capabilities"] for p in providers}
    assert p_map["google-drive"]["browser_oauth"] is True
    assert p_map["google-drive"]["qr_assisted_auth"] is True
    assert p_map["onedrive"]["device_authorization"] is True
    assert p_map["dropbox"]["browser_oauth"] is True

def test_create_device_authorization_session_qr():
    response = client.post("/api/v1/accounts/google-drive/device-session")
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert "verification_url" in data
    assert "qr_code_data_uri" in data
    assert data["qr_code_data_uri"].startswith("data:image/png;base64,")
    
    # Verify no secret tokens or codes are leaked in response
    assert "access_token" not in data
    assert "refresh_token" not in data
    assert "client_secret" not in data

def test_poll_authorization_session_pending_and_cancel():
    # 1. Create session
    create_res = client.post("/api/v1/accounts/onedrive/device-session")
    session_id = create_res.json()["session_id"]

    # 2. Poll status
    poll_res = client.get(f"/api/v1/accounts/authorization-sessions/{session_id}")
    assert poll_res.status_code == 200
    assert poll_res.json()["status"] == "pending"

    # 3. Cancel session
    cancel_res = client.post(f"/api/v1/accounts/authorization-sessions/{session_id}/cancel")
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "success"

    # 4. Verify status is now cancelled
    check_res = client.get(f"/api/v1/accounts/authorization-sessions/{session_id}")
    assert check_res.json()["status"] == "cancelled"

def test_expired_authorization_session():
    create_res = client.post("/api/v1/accounts/dropbox/device-session")
    session_id = create_res.json()["session_id"]
    
    # Simulate session timeout
    AUTH_SESSIONS[session_id]["expires_at"] = datetime.now(timezone.utc) - timedelta(seconds=10)
    
    poll_res = client.get(f"/api/v1/accounts/authorization-sessions/{session_id}")
    assert poll_res.status_code == 200
    assert poll_res.json()["status"] == "expired"
    assert poll_res.json()["seconds_remaining"] == 0

def test_oauth_callback_session_binding():
    # 1. Create session
    create_res = client.post("/api/v1/accounts/google-drive/device-session")
    session_id = create_res.json()["session_id"]

    # 2. Execute simulated callback
    state_param = f"randomstate_usr-admin-1_{session_id}"
    callback_res = client.get(f"/api/v1/accounts/google-drive/callback?code=mock_auth_code_12345&state={state_param}")
    assert callback_res.status_code == 200
    assert callback_res.json()["status"] == "success"

    # 3. Check session marked as authorized
    poll_res = client.get(f"/api/v1/accounts/authorization-sessions/{session_id}")
    assert poll_res.json()["status"] == "authorized"
    assert poll_res.json()["account_id"] is not None
