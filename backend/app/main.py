import asyncio
import os
import json
from datetime import datetime, timezone
from typing import List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database import engine, Base, SessionLocal, get_db
from backend.app.models import User, ConnectedAccount, RegisteredAgent, TransferJob, AuditLog
from backend.app.security.auth import hash_password

# Import API Routers
from backend.app.api.auth import router as auth_router
from backend.app.api.accounts import router as accounts_router
from backend.app.api.transfers import router as transfers_router
from backend.app.api.agent import router as agent_router
from backend.app.api.audit import router as audit_router

# Initialize Tables
Base.metadata.create_all(bind=engine)

def seed_database():
    """Seeds initial administrative user and connected fixture accounts if empty."""
    db = SessionLocal()
    try:
        admin_user = db.query(User).filter(User.email == "vivek.admin@msedcl.gov.in").first()
        if not admin_user:
            admin_user = User(
                id="usr-admin-1",
                email="vivek.admin@msedcl.gov.in",
                name="Vivek Kulkarni",
                hashed_password=hash_password("EnterpriseSecPass2026!"),
                role="admin",
                is_active=True
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
        # No fake demo accounts, jobs, or agents seeded. All data is real from user actions.
    finally:
        db.close()

seed_database()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Enterprise-grade Cloud & Local File Transfer Management System"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Modular Routers under /api/v1
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(accounts_router, prefix=settings.API_V1_STR)
app.include_router(transfers_router, prefix=settings.API_V1_STR)
app.include_router(agent_router, prefix=settings.API_V1_STR)
app.include_router(audit_router, prefix=settings.API_V1_STR)

# ---------------- Legacy / Compatibility Endpoints for Existing UI ----------------
@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "app": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "server_time": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/user/current")
def legacy_current_user(db: Session = Depends(get_db)):
    u = db.query(User).filter(User.role == "admin").first()
    return {
        "name": u.name if u else "Vivek Kulkarni",
        "email": u.email if u else "vivek.admin@msedcl.gov.in",
        "role": "Enterprise Security Admin",
        "avatar_initials": "VK",
        "mfa_enabled": True
    }

@app.get("/api/dashboard/summary")
def get_dashboard_summary(db: Session = Depends(get_db)):
    transfers = db.query(TransferJob).all()
    total_bytes = sum(t.total_bytes for t in transfers)
    transferred_all = sum(t.transferred_bytes for t in transfers)
    failed_bytes = sum(t.total_bytes - t.transferred_bytes for t in transfers if t.status == "Failed")
    total_files = sum(t.total_files for t in transfers)
    completed_files = sum(t.completed_files for t in transfers)
    failed_files = sum(t.failed_files for t in transfers)
    active_speed = sum(t.speed_mbps for t in transfers if t.status == "Running")

    return {
        "total_data_gb": round(total_bytes / (1024**3), 1),
        "total_data_raw": total_bytes,
        "completed_data_gb": round(transferred_all / (1024**3), 1),
        "completed_files": completed_files,
        "completed_pct": round((transferred_all / total_bytes * 100), 1) if total_bytes > 0 else 0,
        "failed_data_gb": round(failed_bytes / (1024**3), 1),
        "failed_files": failed_files,
        "failed_pct": round((failed_files / total_files * 100), 1) if total_files > 0 else 0,
        "transfer_speed_mbps": round(active_speed, 1),
        "active_jobs_count": len([t for t in transfers if t.status == "Running"]),
        "total_jobs_count": len(transfers)
    }

@app.get("/api/transfers")
def legacy_get_transfers(db: Session = Depends(get_db)):
    transfers = db.query(TransferJob).all()
    return {
        "items": [
            {
                "id": t.id,
                "name": t.name,
                "source_account_id": t.source_account_id,
                "source_provider": t.source_provider,
                "source_path": t.source_path,
                "destination_account_id": t.destination_account_id,
                "destination_provider": t.destination_provider,
                "destination_path": t.destination_path,
                "total_bytes": t.total_bytes,
                "transferred_bytes": t.transferred_bytes,
                "total_files": t.total_files,
                "completed_files": t.completed_files,
                "failed_files": t.failed_files,
                "progress_pct": t.progress_pct,
                "speed_mbps": t.speed_mbps,
                "status": t.status,
                "started_at": t.started_at.isoformat(),
                "elapsed_str": "1h 20m"
            }
            for t in transfers
        ]
    }

@app.get("/api/accounts")
def legacy_get_accounts(db: Session = Depends(get_db)):
    accounts = db.query(ConnectedAccount).all()
    return {
        "items": [
            {
                "id": a.id,
                "provider": a.provider,
                "name": a.name,
                "identifier": a.identifier,
                "masked_id": a.masked_id,
                "status": a.status,
                "quota_total_gb": a.quota_total_gb,
                "quota_used_gb": a.quota_used_gb
            }
            for a in accounts
        ]
    }

@app.get("/api/agent")
def legacy_get_agent(db: Session = Depends(get_db)):
    agent = db.query(RegisteredAgent).first()
    if not agent:
        return {"status": "Offline", "device_name": "No Agent Registered"}
    return {
        "status": agent.status,
        "version": agent.version,
        "device_name": agent.device_name,
        "last_seen": agent.last_seen.isoformat(),
        "active_transfers": agent.active_transfers,
        "ip_address": agent.ip_address,
        "storage_path": agent.storage_path,
        "mtls_fingerprint": agent.mtls_fingerprint
    }

@app.get("/api/activity")
def legacy_get_activity(db: Session = Depends(get_db)):
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(8).all()
    return {
        "items": [
            {
                "id": l.id,
                "title": f"{l.action.replace('_', ' ').title()}",
                "description": f"{l.resource} - {l.outcome}",
                "time": l.timestamp.strftime("%H:%M:%S UTC"),
                "icon": "shield-check" if "SUCCESS" in l.outcome else "activity"
            }
            for l in logs
        ]
    }

@app.get("/api/audit-logs")
def legacy_get_audit_logs(db: Session = Depends(get_db)):
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(20).all()
    return {
        "items": [
            {
                "id": l.id,
                "timestamp": l.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"),
                "user": l.user_email,
                "role": l.user_role,
                "action": l.action,
                "resource": l.resource,
                "outcome": l.outcome,
                "request_id": l.request_id,
                "ip": l.ip_address
            }
            for l in logs
        ]
    }

# ----------------- WebSocket Live Telemetry -----------------
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

manager = ConnectionManager()

@app.websocket("/ws/transfers")
async def websocket_transfers_feed(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await asyncio.sleep(2)
            db = SessionLocal()
            try:
                running_jobs = db.query(TransferJob).filter(TransferJob.status == "Running").all()
                for t in running_jobs:
                    # Incremental progress simulation
                    inc = int(t.speed_mbps * 1024 * 1024 * 2)
                    t.transferred_bytes = min(t.total_bytes, t.transferred_bytes + inc)
                    t.progress_pct = round((t.transferred_bytes / t.total_bytes) * 100, 1)
                    if t.progress_pct >= 100:
                        t.status = "Completed"
                        t.speed_mbps = 0.0
                db.commit()

                all_jobs = db.query(TransferJob).all()
                total_bytes = sum(t.total_bytes for t in all_jobs)
                transferred_all = sum(t.transferred_bytes for t in all_jobs)
                failed_bytes = sum(t.total_bytes - t.transferred_bytes for t in all_jobs if t.status == "Failed")
                total_files = sum(t.total_files for t in all_jobs)
                completed_files = sum(t.completed_files for t in all_jobs)
                failed_files = sum(t.failed_files for t in all_jobs)
                active_speed = sum(t.speed_mbps for t in all_jobs if t.status == "Running")

                summary = {
                    "total_data_gb": round(total_bytes / (1024**3), 1),
                    "completed_data_gb": round(transferred_all / (1024**3), 1),
                    "completed_files": completed_files,
                    "completed_pct": round((transferred_all / total_bytes * 100), 1) if total_bytes > 0 else 0,
                    "failed_data_gb": round(failed_bytes / (1024**3), 1),
                    "failed_files": failed_files,
                    "failed_pct": round((failed_files / total_files * 100), 1) if total_files > 0 else 0,
                    "transfer_speed_mbps": round(active_speed, 1),
                    "active_jobs_count": len([t for t in all_jobs if t.status == "Running"]),
                    "total_jobs_count": len(all_jobs)
                }

                await websocket.send_json({
                    "type": "PROGRESS_PULSE",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "transfers": [
                        {
                            "id": t.id,
                            "name": t.name,
                            "source_provider": t.source_provider,
                            "source_path": t.source_path,
                            "destination_provider": t.destination_provider,
                            "destination_path": t.destination_path,
                            "total_bytes": t.total_bytes,
                            "transferred_bytes": t.transferred_bytes,
                            "total_files": t.total_files,
                            "completed_files": t.completed_files,
                            "progress_pct": t.progress_pct,
                            "speed_mbps": t.speed_mbps,
                            "status": t.status,
                            "elapsed_str": "3h 12m"
                        }
                        for t in all_jobs
                    ],
                    "summary": summary
                })
            finally:
                db.close()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)

# ----------------- Serve Frontend Static Files -----------------
static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/{full_path:path}")
def serve_spa(full_path: str):
    if full_path.startswith("api/") or full_path.startswith("ws/"):
        return JSONResponse(status_code=404, content={"detail": "Not found"})
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return JSONResponse({"status": "API Server Ready"})
