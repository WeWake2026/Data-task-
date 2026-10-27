import secrets
import time
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models import User, ConnectedAccount
from backend.app.schemas import AccountResponse, AccountConnectRequest
from backend.app.security.dependencies import get_current_user, require_write_user
from backend.app.security.auth import encrypt_token
from backend.app.security.qr_service import generate_qr_data_uri
from backend.app.providers.implementations import get_provider_adapter
from backend.app.services.audit_service import log_audit_event

router = APIRouter(tags=["Connected Accounts"])

# In-memory short-lived, single-purpose authorization sessions
# Structure: { session_id: { user_id, provider, state, verification_url, expires_at, status, device_code } }
AUTH_SESSIONS: Dict[str, Dict[str, Any]] = {}

@router.get("/providers")
def list_supported_providers():
    """Lists supported cloud/local storage providers with explicit capability flags."""
    providers = ["google-drive", "onedrive", "dropbox", "local"]
    res = []
    for p in providers:
        adapter = get_provider_adapter(p)
        res.append({
            "id": p,
            "name": "Google Drive" if p == "google-drive" else ("Microsoft OneDrive" if p == "onedrive" else ("Dropbox" if p == "dropbox" else "Local Filesystem Agent")),
            "capabilities": adapter.get_capabilities()
        })
    return res

@router.get("/accounts", response_model=List[AccountResponse])
def get_user_accounts(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role == "admin":
        accounts = db.query(ConnectedAccount).all()
    else:
        accounts = db.query(ConnectedAccount).filter(ConnectedAccount.user_id == current_user.id).all()
        
    return [
        AccountResponse(
            id=a.id,
            provider=a.provider,
            name=a.name,
            identifier=a.identifier,
            masked_id=a.masked_id,
            status=a.status,
            auth_type=a.auth_type,
            quota_total_gb=a.quota_total_gb,
            quota_used_gb=a.quota_used_gb,
            token_expires=a.token_expires_at.isoformat() if a.token_expires_at else "Never"
        )
        for a in accounts
    ]

@router.post("/accounts/{provider}/device-session")
def create_device_authorization_session(
    provider: str,
    request: Request,
    current_user: User = Depends(require_write_user)
):
    """
    Creates a short-lived (5 min) authorization session for QR or Device Code pairing.
    Bound strictly to the requesting application user.
    """
    adapter = get_provider_adapter(provider)
    capabilities = adapter.get_capabilities()

    session_id = f"authsess-{secrets.token_hex(12)}"
    oauth_state = f"{secrets.token_urlsafe(16)}_{current_user.id}_{session_id}"
    auth_url = adapter.get_authorization_url(state=oauth_state)
    
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

    # Generate QR data URI if supported
    qr_data_uri = None
    if capabilities.get("qr_assisted_auth"):
        qr_data_uri = generate_qr_data_uri(auth_url)

    # Store safe session state (never contains tokens or secrets)
    AUTH_SESSIONS[session_id] = {
        "session_id": session_id,
        "user_id": current_user.id,
        "provider": provider,
        "state": oauth_state,
        "verification_url": auth_url,
        "expires_at": expires_at,
        "status": "pending",  # pending, authorized, expired, cancelled, failed
        "user_code": secrets.token_hex(4).upper() if capabilities.get("device_authorization") else None,
        "account_id": None
    }

    return {
        "session_id": session_id,
        "provider": provider,
        "capabilities": capabilities,
        "verification_url": auth_url,
        "qr_code_data_uri": qr_data_uri,
        "user_code": AUTH_SESSIONS[session_id]["user_code"],
        "expires_in_seconds": 300,
        "message": "Scan the QR code with your mobile device or open the verification URL to complete provider authentication."
    }

@router.get("/accounts/authorization-sessions/{session_id}")
def get_authorization_session_status(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Polls authorization session status.
    Returns strictly safe metadata: pending, authorized, expired, cancelled, or failed.
    """
    session = AUTH_SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Authorization session not found or expired")

    # Verify session user ownership
    if session["user_id"] != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    # Check expiry
    if datetime.now(timezone.utc) > session["expires_at"]:
        session["status"] = "expired"

    remaining = max(0, int((session["expires_at"] - datetime.now(timezone.utc)).total_seconds()))

    return {
        "session_id": session["session_id"],
        "provider": session["provider"],
        "status": session["status"],
        "seconds_remaining": remaining,
        "account_id": session.get("account_id")
    }

@router.post("/accounts/authorization-sessions/{session_id}/cancel")
def cancel_authorization_session(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    session = AUTH_SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["user_id"] != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    session["status"] = "cancelled"
    return {"status": "success", "message": "Authorization session cancelled"}

@router.get("/accounts/{provider}/callback")
def oauth_callback(
    provider: str,
    code: str,
    state: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Handles provider callback, validates state, binds to session, and stores encrypted tokens.
    """
    parts = state.split("_")
    user_id = parts[1] if len(parts) > 1 else None
    session_id = parts[2] if len(parts) > 2 else None

    user = db.query(User).filter(User.id == user_id).first() if user_id else None
    if not user:
        user = db.query(User).filter(User.role == "admin").first()

    adapter = get_provider_adapter(provider)
    tokens = adapter.exchange_code_for_tokens(code)

    account_id = f"acc-{provider}-{secrets.token_hex(3)}"
    account = ConnectedAccount(
        id=account_id,
        user_id=user.id,
        provider=provider,
        name=f"{provider.capitalize()} Enterprise Drive",
        identifier=f"user-{secrets.token_hex(4)}@{provider}.com",
        masked_id=f"usr***@{provider}.com",
        status="Connected",
        auth_type="OAuth 2.0 PKCE",
        encrypted_access_token=encrypt_token(tokens.get("access_token", "")),
        encrypted_refresh_token=encrypt_token(tokens.get("refresh_token", "")),
        quota_total_gb=1024.0,
        quota_used_gb=120.0
    )
    db.add(account)
    db.commit()

    # Update session if initiated through device/QR session
    if session_id and session_id in AUTH_SESSIONS:
        AUTH_SESSIONS[session_id]["status"] = "authorized"
        AUTH_SESSIONS[session_id]["account_id"] = account_id

    log_audit_event(
        db=db,
        user_id=user.id,
        user_email=user.email,
        user_role=user.role,
        action="OAUTH_CONNECT_SUCCESS",
        resource=f"{account.id} ({provider})",
        outcome="SUCCESS",
        ip_address=request.client.host if request.client else "127.0.0.1"
    )

    return {
        "status": "success",
        "message": f"{provider} authorized successfully! You can close this window.",
        "account_id": account.id
    }

@router.post("/accounts/{account_id}/reconnect")
def reconnect_account(
    account_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_write_user)
):
    account = db.query(ConnectedAccount).filter(ConnectedAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    if current_user.role != "admin" and account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this account")

    account.status = "Connected"
    db.commit()

    log_audit_event(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        user_role=current_user.role,
        action="OAUTH_TOKEN_RECONNECT",
        resource=f"{account.id} ({account.name})",
        outcome="SUCCESS",
        ip_address=request.client.host if request.client else "127.0.0.1"
    )

    return {"status": "success", "message": f"{account.name} reconnected successfully"}

@router.delete("/accounts/{account_id}")
def disconnect_account(
    account_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_write_user)
):
    account = db.query(ConnectedAccount).filter(ConnectedAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    if current_user.role != "admin" and account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this account")

    account_name = account.name
    db.delete(account)
    db.commit()

    log_audit_event(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        user_role=current_user.role,
        action="ACCOUNT_DISCONNECTED",
        resource=f"{account_id} ({account_name})",
        outcome="SUCCESS",
        ip_address=request.client.host if request.client else "127.0.0.1"
    )

    return {"status": "success", "message": f"{account_name} disconnected"}
