from fastapi import APIRouter, Depends, HTTPException, Response, status, Request
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models import User
from backend.app.schemas import UserLogin, UserCreate, TokenResponse, UserResponse
from backend.app.security.auth import verify_password, hash_password, create_access_token, create_refresh_token
from backend.app.security.dependencies import get_current_user
from backend.app.services.audit_service import log_audit_event
from backend.app.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, response: Response, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        # Generic authentication failure to prevent user enumeration
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")

    access_token = create_access_token({"sub": user.id, "email": user.email, "role": user.role})
    refresh_token = create_refresh_token({"sub": user.id})

    # Set secure HttpOnly cookie
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

    log_audit_event(
        db=db,
        user_id=user.id,
        user_email=user.email,
        user_role=user.role,
        action="USER_LOGIN",
        resource="API Session",
        outcome="SUCCESS",
        ip_address=request.client.host if request.client else "127.0.0.1"
    )

    initials = "".join([part[0].upper() for part in user.name.split(" ") if part])[:2]
    user_resp = UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        is_active=user.is_active,
        avatar_initials=initials
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=user_resp
    )

@router.post("/logout")
def logout(response: Response, request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    response.delete_cookie(settings.SESSION_COOKIE_NAME)
    log_audit_event(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        user_role=current_user.role,
        action="USER_LOGOUT",
        resource="API Session",
        outcome="SUCCESS",
        ip_address=request.client.host if request.client else "127.0.0.1"
    )
    return {"status": "success", "message": "Successfully logged out"}

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    initials = "".join([part[0].upper() for part in current_user.name.split(" ") if part])[:2]
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        role=current_user.role,
        is_active=current_user.is_active,
        avatar_initials=initials
    )

# --- Application QR Login Service ---
import secrets
from datetime import datetime, timezone, timedelta
from backend.app.security.qr_service import generate_qr_data_uri

APP_LOGIN_QR_SESSIONS = {}

@router.post("/qr/session")
def create_app_login_qr_session():
    """Generates a secure, 3-minute QR login token for the application login screen."""
    session_id = f"applogin-{secrets.token_hex(16)}"
    qr_auth_url = f"http://127.0.0.1:8000/#/qr-confirm?session_id={session_id}"
    qr_data_uri = generate_qr_data_uri(qr_auth_url)
    
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=3)
    APP_LOGIN_QR_SESSIONS[session_id] = {
        "session_id": session_id,
        "status": "pending",
        "user_id": None,
        "token": None,
        "expires_at": expires_at
    }
    return {
        "session_id": session_id,
        "qr_code_data_uri": qr_data_uri,
        "auth_url": qr_auth_url,
        "expires_in_seconds": 180
    }

@router.get("/qr/status/{session_id}")
def check_app_login_qr_status(session_id: str, response: Response, db: Session = Depends(get_db)):
    """Polls QR login status. If authenticated, attaches the HttpOnly cookie."""
    session = APP_LOGIN_QR_SESSIONS.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="QR login session expired or not found")
    
    if datetime.now(timezone.utc) > session["expires_at"]:
        session["status"] = "expired"

    if session["status"] == "authorized" and session.get("token"):
        response.set_cookie(
            key=settings.SESSION_COOKIE_NAME,
            value=session["token"],
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite=settings.COOKIE_SAMESITE,
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        user = db.query(User).filter(User.id == session["user_id"]).first()
        initials = "".join([part[0].upper() for part in user.name.split(" ") if part])[:2] if user else "US"
        return {
            "status": "authorized",
            "token": session["token"],
            "user": {
                "id": user.id if user else "",
                "email": user.email if user else "",
                "name": user.name if user else "",
                "role": user.role if user else "user",
                "avatar_initials": initials
            }
        }

    return {"status": session["status"]}

@router.post("/qr/authorize-instant")
def authorize_app_login_qr_session(session_id: str, email: str = "vivek.admin@msedcl.gov.in", db: Session = Depends(get_db)):
    """Simulates/handles the mobile scan confirmation for the QR login session."""
    session = APP_LOGIN_QR_SESSIONS.get(session_id)
    if not session or session["status"] != "pending":
        raise HTTPException(status_code=400, detail="Invalid session")
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    access_token = create_access_token({"sub": user.id, "email": user.email, "role": user.role})
    session["status"] = "authorized"
    session["user_id"] = user.id
    session["token"] = access_token
    return {"status": "success", "message": "QR login session approved"}
