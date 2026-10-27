import secrets
import hashlib
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models import User, RegisteredAgent
from backend.app.schemas import AgentEnrollRequest, AgentHeartbeatRequest, AgentResponse
from backend.app.security.dependencies import get_current_user, require_write_user
from backend.app.services.audit_service import log_audit_event

router = APIRouter(prefix="/agents", tags=["Local Windows Agent"])

@router.get("", response_model=List[AgentResponse])
def list_agents(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role == "admin":
        agents = db.query(RegisteredAgent).all()
    else:
        agents = db.query(RegisteredAgent).filter(RegisteredAgent.user_id == current_user.id).all()
    return agents

@router.post("/enroll")
def enroll_agent(
    payload: AgentEnrollRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_write_user)
):
    raw_secret_token = f"sctm_agent_{secrets.token_urlsafe(32)}"
    token_hash = hashlib.sha256(raw_secret_token.encode()).hexdigest()
    
    agent = RegisteredAgent(
        id=f"agent-{secrets.token_hex(4)}",
        user_id=current_user.id,
        device_name=payload.device_name,
        status="Online",
        version=payload.version or "v3.8.2-windows-x64",
        last_seen=datetime.now(timezone.utc),
        ip_address=request.client.host if request.client else "127.0.0.1",
        storage_path=payload.storage_path or "C:\\Transfers",
        mtls_fingerprint=f"SHA256:{secrets.token_hex(16).upper()}",
        api_token_hash=token_hash
    )
    db.add(agent)
    db.commit()

    log_audit_event(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        user_role=current_user.role,
        action="AGENT_ENROLLED",
        resource=f"{agent.id} ({payload.device_name})",
        outcome="SUCCESS",
        ip_address=request.client.host if request.client else "127.0.0.1"
    )

    return {
        "status": "success",
        "agent_id": agent.id,
        "device_name": agent.device_name,
        "agent_token": raw_secret_token,
        "instructions": "Save this token securely into agent config.json. It will never be shown again."
    }

@router.post("/{agent_id}/heartbeat")
def agent_heartbeat(
    agent_id: str,
    payload: AgentHeartbeatRequest,
    db: Session = Depends(get_db)
):
    agent = db.query(RegisteredAgent).filter(RegisteredAgent.id == agent_id).first()
    if not agent or agent.status == "Revoked":
        raise HTTPException(status_code=403, detail="Agent unrecognized or revoked")
    
    agent.last_seen = datetime.now(timezone.utc)
    agent.active_transfers = payload.active_transfers
    db.commit()

    return {"status": "success", "acknowledged": True}

@router.delete("/{agent_id}")
def revoke_agent(
    agent_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_write_user)
):
    agent = db.query(RegisteredAgent).filter(RegisteredAgent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if current_user.role != "admin" and agent.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to revoke this agent")

    agent.status = "Revoked"
    db.commit()

    log_audit_event(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        user_role=current_user.role,
        action="AGENT_REVOKED",
        resource=f"{agent.id} ({agent.device_name})",
        outcome="SUCCESS",
        ip_address=request.client.host if request.client else "127.0.0.1"
    )

    return {"status": "success", "message": f"Agent {agent.device_name} revoked successfully"}
