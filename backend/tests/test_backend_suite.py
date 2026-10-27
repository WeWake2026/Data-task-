import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.security.auth import hash_password, verify_password, create_access_token, decode_token, encrypt_token, decrypt_token

client = TestClient(app)

def test_password_hashing():
    plain = "SuperSecretPassword2026!"
    hashed = hash_password(plain)
    assert hashed != plain
    assert verify_password(plain, hashed) is True
    assert verify_password("WrongPassword", hashed) is False

def test_token_creation_and_decoding():
    payload = {"sub": "usr-test-123", "role": "admin"}
    token = create_access_token(payload)
    decoded = decode_token(token)
    assert decoded["sub"] == "usr-test-123"
    assert decoded["role"] == "admin"

def test_token_encryption_at_rest():
    secret_oauth_token = "ya29.a0AfH6SMC_secret_cloud_token_xyz"
    encrypted = encrypt_token(secret_oauth_token)
    assert encrypted != secret_oauth_token
    decrypted = decrypt_token(encrypted)
    assert decrypted == secret_oauth_token

def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_dashboard_summary():
    response = client.get("/api/dashboard/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_data_gb" in data
    assert "completed_data_gb" in data
    assert "completed_files" in data

def test_auth_login_success_and_cookie():
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "vivek.admin@msedcl.gov.in", "password": "EnterpriseSecPass2026!"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["email"] == "vivek.admin@msedcl.gov.in"
    assert "sctm_session" in response.cookies

def test_auth_login_invalid_password_generic_error():
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "vivek.admin@msedcl.gov.in", "password": "WrongPassword123"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"

def test_accounts_listing():
    # 1. Connect a real account via OAuth callback
    state_param = "teststate_usr-admin-1"
    client.get(f"/api/v1/accounts/google-drive/callback?code=real_test_code_99&state={state_param}")
    
    response = client.get("/api/v1/accounts")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    # Check that raw tokens are NEVER exposed in response
    for acc in data:
        assert "encrypted_access_token" not in acc
        assert "encrypted_refresh_token" not in acc

def test_transfers_listing_and_action():
    # 1. Ensure source & destination accounts exist
    client.get("http://127.0.0.1:8000/api/v1/accounts/onedrive/callback?code=ms_code_11&state=test_usr-admin-1")
    accounts = client.get("/api/v1/accounts").json()
    src_id = accounts[0]["id"]
    dst_id = accounts[-1]["id"]

    # 2. Create real transfer job
    create_res = client.post(
        "/api/v1/transfers",
        json={
            "name": "Live Real Substation Sync",
            "source_account_id": src_id,
            "source_path": "/Engineering/SCADA",
            "destination_account_id": dst_id,
            "destination_path": "/Backup/SCADA",
            "concurrency": 4
        }
    )
    assert create_res.status_code == 201
    job_id = create_res.json()["job"]["id"]

    # 3. List transfers
    response = client.get("/api/v1/transfers")
    assert response.status_code == 200
    jobs = response.json()
    assert len(jobs) >= 1

    # 4. Test pause action
    action_res = client.post(f"/api/v1/transfers/{job_id}/pause")
    assert action_res.status_code == 200
    assert action_res.json()["transfer"]["status"] == "Paused"

    # 5. Test resume action
    resume_res = client.post(f"/api/v1/transfers/{job_id}/resume")
    assert resume_res.status_code == 200
    assert resume_res.json()["transfer"]["status"] == "Running"

def test_agent_enrollment_and_heartbeat():
    client.post(
        "/api/v1/auth/login",
        json={"email": "vivek.admin@msedcl.gov.in", "password": "EnterpriseSecPass2026!"}
    )
    enroll_res = client.post(
        "/api/v1/agents/enroll",
        json={"device_name": "WIN11-TEST-WORKSTATION", "version": "v3.8.2-windows-x64"}
    )
    assert enroll_res.status_code == 200
    agent_data = enroll_res.json()
    agent_id = agent_data["agent_id"]
    assert "agent_token" in agent_data

    # Send heartbeat
    hb_res = client.post(
        f"/api/v1/agents/{agent_id}/heartbeat",
        json={"agent_id": agent_id, "active_transfers": 0, "throughput_mbps": 0.0}
    )
    assert hb_res.status_code == 200
    assert hb_res.json()["acknowledged"] is True
